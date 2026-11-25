#!/usr/bin/env python3
"""
ĐT05 - Tóm tắt tin tức kinh tế có kiểm chứng dữ kiện
Script chuẩn bị dữ liệu: lọc -> làm sạch -> loại trùng -> chọn mẫu -> chia dev/test.

Chạy:
    pip install datasets pandas scikit-learn
    python data/prepare_data.py                     # mặc định: 60 bài (10 dev / 50 test)
    python data/prepare_data.py --n 60 --n-dev 10 --seed 42

Đầu ra (trong thư mục --out, mặc định "."):
    data/processed/selected_articles.jsonl    (CÓ TOÀN VĂN -> KHÔNG đẩy lên repo công khai)
    data/processed/numeric_facts_audit.csv    (số liệu trích bằng regex, để rà soát tay)
    data/data_manifest.csv
    data/splits/dev_ids.txt, test_ids.txt, selection_config.json
    data/annotations/gold_summaries.csv       (template, chưa có gold; gồm draft_source)
    data/annotations/gold_numeric_facts.csv   (template trống, mỗi fact một dòng)
    data/annotations/pilot_drafts.csv         (template trống cho hai bản viết độc lập)
    data/annotations/review_log.csv           (template trống, gồm decision/reason)
    reports/data_quality_report.md            (bản tự sinh, cần bổ sung nhận xét tay)
    reports/excluded_items.csv
"""
import argparse
import hashlib
import html
import json
import math
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

REPO = "VLUS06/VietOnlineNews"
REVISION = "bd8d2a865c8981d34cb9d85f69f62bda7c40b520"
RETRIEVED_AT = "2026-11-25T09:51:48+07:00"
SOURCE_URL = "https://huggingface.co/datasets/VLUS06/VietOnlineNews"
GUIDELINE_VERSION = "v1.0"

# ----------------------------------------------------------------------------
# Trích số liệu, gồm đơn vị ghép như USD/tấn và đồng/USD.
# ----------------------------------------------------------------------------
NUM = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
UNITS = [
    "triệu đồng/lượng", "triệu đồng/lần", "triệu đồng/m2", "triệu đồng/năm",
    "triệu NDT/năm", "tỷ đồng/căn hộ", "tỷ đồng/tháng",
    "USD/ounce", "USD/tấn", "USD/kg", "đồng/USD", "đồng/CP",
    "đồng/bánh", "đồng/kg", "%/năm", "con/phụ nữ", "giờ/ngày",
    "mẫu/ngày", "ngày/tuần",
    "nghìn tỷ đồng", "nghìn tỷ", "triệu tỷ", "tỷ đồng", "tỷ USD", "tỷ đô la", "tỷ đô",
    "triệu USD", "triệu đô la", "triệu đồng", "nghìn đồng", "điểm phần trăm", "phần trăm",
    "%", "USD", "đô la", "VND", "VNĐ", "đồng", "tỷ", "triệu", "nghìn", "ngàn", "điểm",
    "tấn", "kg", "ha", "m2", "m²", "cổ phiếu", "lượng", "chỉ",
]
UNITS.sort(key=len, reverse=True)  # khớp đơn vị dài trước
FACT_RE = re.compile(
    rf"(?<![\w.,/])({NUM})\s?({'|'.join(re.escape(u) for u in UNITS)})(?!\w)(?!\s?nghiệp)", re.IGNORECASE
)
PERIOD_RE = re.compile(
    r"(?:quý\s+(?:IV|III|II|I|[1-4])(?:\s?/\s?\d{4})?|tháng\s+\d{1,2}(?:\s?/\s?\d{4})?"
    r"|(?<!\d)\d{1,2}\s+tháng(?:\s+đầu\s+năm(?:\s+\d{4})?)?"
    r"|năm\s+\d{4}|(?<!\d)\d{1,2}/\d{1,2}/\d{4}|(?<!\d)\d{1,2}/\d{4})",
    re.IGNORECASE,
)
DOT_DECIMAL_PCT_RE = re.compile(r"(?<![\w.,])\d+\.\d{1,2}\s?%")  # 3.2% (kiểu số Anh) - cờ cảnh báo
TAG_RE = re.compile(r"<[^>]+>")

TOPIC_KEYWORDS = {
    "vi_mo": ["gdp", "cpi", "lạm phát", "tăng trưởng", "tổng cục thống kê", "kinh tế vĩ mô", "pmi"],
    "tien_te_ngan_hang": ["tỷ giá", "lãi suất", "ngân hàng nhà nước", "tín dụng", "ngân hàng", "nợ xấu", "trái phiếu"],
    "chung_khoan": ["vn-index", "vnindex", "chứng khoán", "cổ phiếu", "thanh khoản", "khối ngoại"],
    "xuat_nhap_khau": ["xuất khẩu", "nhập khẩu", "xuất siêu", "nhập siêu", "thuế quan", "thương mại"],
    "doanh_nghiep": ["doanh thu", "lợi nhuận", "báo cáo tài chính", "doanh nghiệp", "cổ tức"],
    "bat_dong_san": ["bất động sản", "căn hộ", "giá nhà", "đất nền", "chung cư", "dự án"],
    "hang_hoa": ["giá vàng", "xăng dầu", "giá dầu", "giá gạo", "cà phê", "giá heo", "giá thép"],
}


def clean_text(s: str) -> str:
    s = html.unescape(s or "")
    s = TAG_RE.sub(" ", s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s)
    return s.strip()


def extract_facts(text: str):
    seen, out = set(), []
    for m in FACT_RE.finditer(text):
        key = (m.group(1), m.group(2).lower())
        if key not in seen:
            seen.add(key)
            out.append({"raw": m.group(0), "value": m.group(1), "unit": m.group(2)})
    return out


def assign_topic(title: str, content: str) -> str:
    low = f"{title} {content}".lower()
    scores = {t: sum(low.count(k) for k in kws) for t, kws in TOPIC_KEYWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "khac"


def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower()).strip()


def apply_drop(df, mask, reason, steps, excluded):
    for i in df.loc[mask, "id"]:
        excluded.append((i, reason))
    steps.append((reason, int(mask.sum()), int((~mask).sum())))
    return df[~mask].copy()


def pick(cands, need, chosen, sim, thr):
    """Chọn lần lượt theo vòng tròn các chủ đề, bỏ ứng viên quá giống bài đã chọn (cùng sự kiện)."""
    out = []
    topics = list(cands)
    while len(out) < need and any(cands.values()):
        progressed = False
        for t in topics:
            while cands[t]:
                i = cands[t].pop()
                if all(sim[i, j] < thr for j in chosen + out):
                    out.append(i)
                    progressed = True
                    break
            if len(out) >= need:
                break
        if not progressed:
            break
    return out


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=".")
    p.add_argument("--categories", nargs="+", default=["Kinh doanh", "Bất động sản"])
    p.add_argument("--n", type=int, default=60, help="tổng số bài chọn (>=50; dư để phòng bài bị loại khi gắn nhãn)")
    p.add_argument("--n-dev", type=int, default=10)
    p.add_argument("--min-words", type=int, default=250)
    p.add_argument("--max-words", type=int, default=900)
    p.add_argument("--min-facts", type=int, default=4, help="số dữ kiện định lượng tối thiểu để tính là 'bài có số liệu'")
    p.add_argument("--rich-frac", type=float, default=0.8, help="tỷ lệ bài có số liệu trong mẫu chọn")
    p.add_argument("--pool", type=int, default=4000, help="số bài lấy ngẫu nhiên để xét trùng/chọn mẫu")
    p.add_argument("--dup-sim", type=float, default=0.8, help="ngưỡng cosine coi là bản đăng lại/gần trùng")
    p.add_argument("--event-sim", type=float, default=0.4, help="ngưỡng cosine tránh chọn 2 bài cùng sự kiện")
    p.add_argument("--cross-frac", type=float, default=0.25, help="tỷ lệ bài đánh dấu cần hậu kiểm chéo (>=0.2)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--revision", default=REVISION)
    return p.parse_args()


def main():
    a = parse_args()
    rng = random.Random(a.seed)
    out = Path(a.out)
    if (out / "data/splits/split_history.json").exists():
        raise SystemExit(
            "Split lock history already exists; refusing to overwrite the locked IDs. "
            "Use a fresh --out directory for a new preparation run."
        )
    for d in ["data/processed", "data/splits", "data/annotations", "reports"]:
        (out / d).mkdir(parents=True, exist_ok=True)
    steps, excluded = [], []

    # 1. Tải dữ liệu (cố định revision) --------------------------------------
    from datasets import load_dataset

    dsd = load_dataset(REPO, revision=a.revision)
    need_cols = {"id", "title", "description", "content", "category"}
    frames, total_raw, cat_dist_all = [], 0, Counter()
    for sp, ds in dsd.items():
        assert need_cols <= set(ds.column_names), f"Thiếu cột ở split {sp}: {ds.column_names}"
        total_raw += len(ds)
        cat_dist_all.update(ds["category"])
        sub = ds.filter(lambda x: x["category"] in a.categories)
        d = sub.to_pandas()[["id", "title", "description", "content", "category"]]
        d["hf_split"] = sp
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["id"] = df["id"].astype(str)
    steps.append((f"Tổng số dòng ban đầu (mọi split, 13 chuyên mục)", 0, total_raw))
    steps.append((f"Giữ chuyên mục {a.categories}", total_raw - len(df), len(df)))

    # 2. Làm sạch + cờ chất lượng -------------------------------------------
    raw_content = df["content"].fillna("").astype(str)
    df["flag_html"] = raw_content.map(lambda s: bool(TAG_RE.search(s)))
    df["flag_nfc_changed"] = raw_content.map(lambda s: s != unicodedata.normalize("NFC", s))
    for c in ["title", "description", "content"]:
        df[c] = df[c].fillna("").astype(str).map(clean_text)

    # 3. Lọc theo bước, ghi lý do từng ID ------------------------------------
    df = apply_drop(df, df.duplicated("id"), "ID trùng", steps, excluded)
    df = apply_drop(df, (df["title"] == "") | (df["content"] == ""), "Tiêu đề/nội dung rỗng", steps, excluded)
    df = apply_drop(df, df["content"].map(lambda s: md5(norm_ws(s))).duplicated(), "Trùng nội dung chính xác", steps, excluded)
    df = apply_drop(df, df["title"].map(norm_ws).duplicated(), "Trùng tiêu đề", steps, excluded)
    df["n_words"] = df["content"].str.split().str.len()
    df = apply_drop(df, (df["n_words"] < a.min_words) | (df["n_words"] > a.max_words),
                    f"Độ dài ngoài [{a.min_words}, {a.max_words}] từ", steps, excluded)

    # 4. Lấy pool ngẫu nhiên, trích số liệu, xét gần trùng -------------------
    if len(df) > a.pool:
        steps.append((f"Lấy ngẫu nhiên pool {a.pool} bài (seed={a.seed}) - bước lấy mẫu, không phải loại lỗi",
                      len(df) - a.pool, a.pool))
        df = df.sample(n=a.pool, random_state=a.seed)
    df = df.reset_index(drop=True)
    df["facts"] = df["content"].map(extract_facts)
    df["n_facts"] = df["facts"].map(len)
    df["n_periods"] = df["content"].map(lambda s: len(PERIOD_RE.findall(s)))
    df["flag_dot_decimal_pct"] = df["content"].map(lambda s: bool(DOT_DECIMAL_PCT_RE.search(s)))
    df["topic"] = [assign_topic(t, c) for t, c in zip(df["title"], df["content"])]

    sim_text = (df["title"] + " " + df["content"].str[:600]).tolist()
    X = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, dtype=np.float32).fit_transform(sim_text)
    sim = (X @ X.T).toarray()
    np.fill_diagonal(sim, 0.0)
    keep = []
    dup_mask = np.zeros(len(df), dtype=bool)
    for i in range(len(df)):
        if keep and sim[i, keep].max() >= a.dup_sim:
            dup_mask[i] = True
        else:
            keep.append(i)
    n_dup = int(dup_mask.sum())
    for i in np.where(dup_mask)[0]:
        excluded.append((df.loc[i, "id"], f"Gần trùng (cosine >= {a.dup_sim}) với bài khác trong pool"))
    steps.append((f"Gần trùng/đăng lại (TF-IDF cosine >= {a.dup_sim})", n_dup, len(keep)))
    sim = sim[np.ix_(keep, keep)]
    df = df.iloc[keep].reset_index(drop=True)

    # 5. Chọn mẫu: đa dạng chủ đề, tránh cùng sự kiện ------------------------
    n_rich = round(a.n * a.rich_frac)
    n_low = a.n - n_rich
    order = list(TOPIC_KEYWORDS) + ["khac"]
    rng.shuffle(order)

    def build_cands(mask):
        c = {t: [] for t in order}
        idx = list(np.where(mask)[0])
        rng.shuffle(idx)
        for i in idx:
            c[df.loc[i, "topic"]].append(i)
        return c

    rich_mask = (df["n_facts"] >= a.min_facts).values
    low_mask = (df["n_facts"] < a.min_facts).values
    chosen = pick(build_cands(rich_mask), n_rich, [], sim, a.event_sim)
    chosen += pick(build_cands(low_mask), n_low, chosen, sim, a.event_sim)
    if len(chosen) < a.n:  # bù nếu thiếu: nới sang nhóm còn lại
        rest = build_cands(np.ones(len(df), dtype=bool))
        for t in rest:
            rest[t] = [i for i in rest[t] if i not in chosen]
        chosen += pick(rest, a.n - len(chosen), chosen, sim, a.event_sim)
    if len(chosen) < a.n:
        print(f"[CẢNH BÁO] Chỉ chọn được {len(chosen)}/{a.n} bài. Hãy tăng --pool hoặc nới --max-words/--event-sim.")

    sel = df.loc[chosen].copy().sort_values("id").reset_index(drop=True)
    sel["item_id"] = [f"DT05-{i + 1:03d}" for i in range(len(sel))]
    steps.append((f"Chọn mẫu cuối (đa dạng chủ đề, event-sim < {a.event_sim})", len(df) - len(sel), len(sel)))

    # 6. Chia dev/test (dev có cả bài nhiều và ít số liệu) ------------------
    rich_ids = sel.index[sel["n_facts"] >= a.min_facts].tolist()
    low_ids = sel.index[sel["n_facts"] < a.min_facts].tolist()
    dev_rich = min(len(rich_ids), round(a.n_dev * len(rich_ids) / max(len(sel), 1)))
    dev_idx = rng.sample(rich_ids, dev_rich) + rng.sample(low_ids, min(len(low_ids), a.n_dev - dev_rich))
    sel["split"] = np.where(sel.index.isin(dev_idx), "dev", "test")
    sel["has_numbers"] = sel["n_facts"] >= a.min_facts

    n_cross = math.ceil(a.cross_frac * len(sel))
    cross_idx = set(rng.sample(range(len(sel)), n_cross))
    sel["cross_review_required"] = [i in cross_idx for i in range(len(sel))]

    # 7. Ghi tệp --------------------------------------------------------------
    with open(out / "data/processed/selected_articles.jsonl", "w", encoding="utf-8") as f:
        for _, r in sel.iterrows():
            f.write(json.dumps({
                "item_id": r.item_id, "document_id": r.id, "split": r.split, "title": r.title,
                "description": r.description, "content": r.content, "original_category": r.category,
                "topic": r.topic, "n_words": int(r.n_words), "n_facts": int(r.n_facts),
                "n_periods": int(r.n_periods), "has_numbers": bool(r.has_numbers),
            }, ensure_ascii=False) + "\n")

    pd.DataFrame([
        {"item_id": r.item_id, "document_id": r.id, "raw": f_["raw"], "value": f_["value"], "unit": f_["unit"],
         "checked_by": "", "ok": ""}
        for _, r in sel.iterrows() for f_ in r.facts
    ]).to_csv(out / "data/processed/numeric_facts_audit.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame({
        "item_id": sel.item_id, "document_id": sel.id, "source_name": REPO, "source_url": SOURCE_URL,
        "source_version": a.revision, "retrieved_at": RETRIEVED_AT, "published_at": "unknown",
        "language": "vi", "original_category": sel.category, "task_label": "summary_reference_v1.0",
        "license_status": "OTHER_UNVERIFIED", "split": sel.split,
        "notes": [f"topic={t};n_facts={n};n_words={w};has_numbers={h};hf_split={s}"
                  for t, n, w, h, s in zip(sel.topic, sel.n_facts, sel.n_words, sel.has_numbers, sel.hf_split)],
    }).to_csv(out / "data/data_manifest.csv", index=False, encoding="utf-8-sig")

    (out / "data/splits/dev_ids.txt").write_text("\n".join(sel.loc[sel.split == "dev", "item_id"]) + "\n", encoding="utf-8")
    (out / "data/splits/test_ids.txt").write_text("\n".join(sel.loc[sel.split == "test", "item_id"]) + "\n", encoding="utf-8")
    (out / "data/splits/selection_config.json").write_text(
        json.dumps({**vars(a), "repo": REPO, "retrieved_at": RETRIEVED_AT}, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.DataFrame({
        "item_id": sel.item_id, "document_id": sel.id, "split": sel.split, "title": sel.title,
        "description_ref_NOT_GOLD": sel.description, "reference_summary": "", "draft_source": "",
        "annotator_id": "", "reviewer_id": "", "review_status": "todo",
        "guideline_version": GUIDELINE_VERSION,
        "cross_review_required": sel.cross_review_required, "has_numbers": sel.has_numbers, "disagreement_note": "",
    }).to_csv(out / "data/annotations/gold_summaries.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=[
        "item_id", "fact_id", "entity", "indicator", "value", "unit", "period",
        "comparison_basis", "modality", "source_sentence", "annotator_id", "notes",
    ]).to_csv(out / "data/annotations/gold_numeric_facts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=[
        "item_id", "annotator_id", "draft_summary", "draft_source", "created_at",
    ]).to_csv(out / "data/annotations/pilot_drafts.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(columns=[
        "item_id", "decision", "reason", "annotator_id", "reviewer_id", "disagreement",
        "resolution", "guideline_version", "reviewed_at",
    ]).to_csv(
        out / "data/annotations/review_log.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(excluded, columns=["document_id", "reason"]).to_csv(
        out / "reports/excluded_items.csv", index=False, encoding="utf-8-sig")

    # 8. Báo cáo chất lượng dữ liệu (tự sinh) ---------------------------------
    L = ["# Data Quality Report (tự sinh bởi data/prepare_data.py)", "",
         f"- Dataset: `{REPO}` | revision: `{a.revision}` | retrieved_at: {RETRIEVED_AT}",
         f"- Seed: {a.seed} | guideline: {GUIDELINE_VERSION}",
         "- `published_at` = unknown (dataset không có cột ngày đăng; không suy ra từ ngày tải).",
         "- license_status = OTHER_UNVERIFIED: Hub khai báo `other`, nhưng quyền sử dụng/tái phân phối chưa được xác minh.", "",
         "## 1. Kiểm đếm trước/sau từng bước", "", "| Bước | Số bị loại | Còn lại |", "|---|---:|---:|"]
    L += [f"| {r} | {x} | {y} |" for r, x, y in steps]
    L += ["", "Danh sách ID bị loại và lý do: `reports/excluded_items.csv`.", "",
          "## 2. Phân bố chuyên mục của toàn dataset (13 nhãn gốc)", "", "| Chuyên mục | Số bài |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in cat_dist_all.most_common()]
    L += ["", "## 3. Mẫu đã chọn", "",
          f"- Tổng: {len(sel)} | dev: {(sel.split == 'dev').sum()} | test: {(sel.split == 'test').sum()}",
          f"- Bài có số liệu (>= {a.min_facts} dữ kiện): {int(sel.has_numbers.sum())} | "
          f"dev: {int(sel[sel.split == 'dev'].has_numbers.sum())} | test: {int(sel[sel.split == 'test'].has_numbers.sum())}",
          f"- Bài đánh dấu hậu kiểm chéo: {int(sel.cross_review_required.sum())} ({sel.cross_review_required.mean():.0%})",
          f"- Số từ: min {sel.n_words.min()}, trung vị {int(sel.n_words.median())}, max {sel.n_words.max()}",
          f"- Số dữ kiện định lượng/bài: min {sel.n_facts.min()}, trung vị {int(sel.n_facts.median())}, max {sel.n_facts.max()}",
          "", "| Chuyên mục gốc | Số bài |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in sel.category.value_counts().items()]
    L += ["", "| Chủ đề (gán bằng từ khóa) | Tổng | Dev | Test |", "|---|---:|---:|---:|"]
    for t, g in sel.groupby("topic"):
        L.append(f"| {t} | {len(g)} | {(g.split == 'dev').sum()} | {(g.split == 'test').sum()} |")
    L += ["", "## 4. Cờ chất lượng trong mẫu chọn", "",
          f"- Nội dung còn thẻ HTML trước khi làm sạch: {int(sel.flag_html.sum())}",
          f"- Nội dung bị đổi khi chuẩn hóa Unicode NFC: {int(sel.flag_nfc_changed.sum())}",
          f"- Bài có số kiểu dấu chấm thập phân (vd 3.2%) cần xem tay: {int(sel.flag_dot_decimal_pct.sum())} "
          f"-> {', '.join(sel.loc[sel.flag_dot_decimal_pct, 'item_id']) or 'không có'}",
          f"- Bài ít/không có số liệu: {int((~sel.has_numbers).sum())}",
          "- Rà soát số liệu: các biểu thức regex chỉ tạo ứng viên; cần đối chiếu ngữ cảnh, đơn vị, kỳ và ý nghĩa. Mẫu kiểm tra nằm ở mục 7.",
          "", "## 5. Chống rò rỉ (leakage)", "",
          f"- Gần trùng loại bỏ ở ngưỡng cosine {a.dup_sim}; khi chọn mẫu, không chọn 2 bài có cosine >= {a.event_sim} "
          "(tránh cùng sự kiện nằm ở cả dev và test).",
          "- Mỗi bài chỉ xuất hiện đúng một lần (một bài = một mẫu, không chia chunk).",
          "- Giới hạn: kiểm tra trùng chỉ thực hiện trong pool ngẫu nhiên, không trên toàn bộ dataset; TF-IDF không "
          "bắt được bài viết lại bằng từ ngữ khác. Mẫu rà cặp tiêu đề và cảnh báo loại nhầm được ghi ở mục 7.",
          "", "## 6. Danh sách bài đã chọn", "",
          "| item_id | document_id | split | chủ đề | số từ | số dữ kiện | tiêu đề |", "|---|---|---|---|---:|---:|---|"]
    for _, r in sel.iterrows():
        L.append(f"| {r.item_id} | {r.id} | {r.split} | {r.topic} | {r.n_words} | {r.n_facts} | {r.title[:70].replace('|', '/')} |")
    report_path = out / "reports/data_quality_report.md"
    previous_report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
    manual_start = previous_report.find("\n## 7. Kiểm tra thủ công")
    if manual_start >= 0:
        L.extend(["", previous_report[manual_start + 1:].rstrip()])
    report_path.write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"Xong: {len(sel)} bài (dev {(sel.split == 'dev').sum()}, test {(sel.split == 'test').sum()}).")
    print("Mở reports/data_quality_report.md để xem thống kê; đọc tay danh sách tiêu đề để kiểm tra trùng sự kiện.")


if __name__ == "__main__":
    main()
