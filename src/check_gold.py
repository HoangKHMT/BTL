#!/usr/bin/env python3
"""
ĐT05 - Tự kiểm gold (tóm tắt tham chiếu + phiếu số liệu).

Chạy (từ thư mục gốc repo):
    python src/check_gold.py                       # kiểm mọi bài đã có tóm tắt
    python src/check_gold.py --locked-version v1.0 # sau khi khóa guideline
    python src/check_gold.py --items DT05-001 DT05-002

Mức độ:
    ERROR  = vi phạm quy tắc mà máy kiểm chắc chắn được (exit code 1)
    WARN   = nghi vấn, nên xem lại
    REVIEW = máy KHÔNG xác nhận được, bắt buộc người xem lại (vd số dạng 3.2%)

GIỚI HẠN QUAN TRỌNG: script chỉ so khớp chuỗi/số với thân bài. Nó KHÔNG xác nhận được chủ thể đúng,
kỳ/cơ sở so sánh đúng, dự báo hay thực tế, ý chính, hay ý nghĩa của số dạng dấu chấm thập phân.
Không có lỗi KHÔNG có nghĩa là gold đúng; người rà soát vẫn phải kiểm tay.
"""
import argparse
import difflib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "data"))
from prepare_data import FACT_RE, NUM, PERIOD_RE, clean_text  # noqa: E402

STATUSES = {"todo", "annotated", "reviewed", "exclude"}
MODALITIES = {"actual", "estimate", "forecast", "target", "proposal", "planned"}
DRAFT_SOURCES = {"human", "llm_edited"}
SHEET_REQUIRED = ["entity", "indicator", "value", "period", "modality", "source_sentence", "annotator_id"]

# Số dạng dấu chấm thập phân (3.2, 3.25%): xử lý riêng, KHÔNG nằm trong FACT_RE.
DOTDEC_RE = re.compile(r"(?<![\w.,])(\d+\.\d{1,2})(?![\d\w])(\s?%)?")
TOKEN_RE = re.compile(rf"(?<![\w.,])({NUM})(?!\w)")
BULLET_RE = re.compile(r"(?m)^\s*(?:[-*•#]+|\d+[.)])\s")
PROTECT_ABBR = re.compile(r"\b(TP|Tp|TS|ThS|PGS|GS|Q|P)\.")
NON_METRIC_IDENTIFIER_RE = re.compile(r"\bS\s*&\s*P\s*500\b", re.IGNORECASE)


# ----------------------------------------------------------------------------- tiện ích
def to_float(s: str) -> float:
    s = s.strip()
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    return float(s)


def unorm(u: str) -> str:
    u = re.sub(r"\s+", " ", (u or "").strip().lower())
    return "%" if u == "phần trăm" else u


def unit_related(a: str, b: str) -> bool:
    """Match shortened units and units with an added denominator."""
    return a != b and (
        a.startswith(b + " ")
        or b.startswith(a + " ")
        or a.startswith(b + "/")
        or b.startswith(a + "/")
    )


def norm_text(s: str) -> str:
    s = clean_text(s).replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    return re.sub(r"\s+", " ", s).strip()


def split_sentences(text: str):
    t = PROTECT_ABBR.sub(lambda m: m.group(1) + "\u2024", norm_text(text))
    pieces = re.split(r"(?<=[.!?…])\s+", t)
    out = []
    for p in pieces:
        if out and p and p[0].islower():
            out[-1] += " " + p  # nối lại: viết tắt hoặc câu bị cắt nhầm
        elif p:
            out.append(p)
    return [s.replace("\u2024", ".") for s in out]


def analyze(text: str):
    """Trích số, số kèm đơn vị, số dạng chấm thập phân và mốc thời gian từ một đoạn văn."""
    text = re.sub(r"(m2|m²)(?=[A-Za-zÀ-ỹ])", r"\1 ", text, flags=re.IGNORECASE)
    dotdec = [(m.group(1), "%" if m.group(2) else "") for m in DOTDEC_RE.finditer(text)]
    masked = DOTDEC_RE.sub(lambda m: " " * len(m.group(0)), text)
    period_spans = [m.span() for m in PERIOD_RE.finditer(masked)]
    ignored_spans = period_spans + [m.span() for m in NON_METRIC_IDENTIFIER_RE.finditer(masked)]
    periods = [re.sub(r"\s+", "", m.group(0).lower()) for m in PERIOD_RE.finditer(masked)]
    facts, fact_starts = [], set()
    for m in FACT_RE.finditer(masked):
        facts.append((m.group(1), unorm(m.group(2))))
        fact_starts.add(m.start(1))
    tokens, bare = [], []
    for m in TOKEN_RE.finditer(masked):
        if any(s <= m.start() and m.end() <= e for s, e in ignored_spans):
            continue
        tokens.append(m.group(1))
        if m.start(1) not in fact_starts:
            bare.append(m.group(1))
    return {"dotdec": dotdec, "facts": facts, "tokens": tokens, "bare": bare, "periods": periods}


def vtuple(s: str):
    m = re.match(r"\s*v?(\d+)(?:\.(\d+))?", (s or "").lower())
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--items", nargs="*", default=None)
    ap.add_argument("--locked-version", default=None, help="vd v1.0; chưa khóa thì bỏ trống")
    ap.add_argument("--min-sent", type=int, default=3)
    ap.add_argument("--max-sent", type=int, default=5)
    ap.add_argument("--min-words", type=int, default=50)
    ap.add_argument("--max-words", type=int, default=120)
    ap.add_argument("--strict", action="store_true", help="WARN cũng làm exit code = 1")
    a = ap.parse_args()
    root = Path(a.root)

    paths = {
        "gold": root / "data/annotations/gold_summaries.csv",
        "sheet": root / "data/annotations/gold_numeric_facts.csv",
        "log": root / "data/annotations/review_log.csv",
        "articles": root / "data/processed/selected_articles.jsonl",
        "dev": root / "data/splits/dev_ids.txt",
        "test": root / "data/splits/test_ids.txt",
    }
    for k in ("gold", "articles"):
        if not paths[k].exists():
            print(f"Thiếu tệp bắt buộc: {paths[k]}")
            sys.exit(2)

    rd = lambda p: pd.read_csv(p, encoding="utf-8-sig", dtype=str).fillna("")
    gold = rd(paths["gold"]).to_dict("records")
    sheet = rd(paths["sheet"]).to_dict("records") if paths["sheet"].exists() else []
    log_ids = {r["item_id"] for r in rd(paths["log"]).to_dict("records")} if paths["log"].exists() else set()
    arts = {}
    for line in paths["articles"].read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            arts[d["item_id"]] = d
    dev_ids = set(paths["dev"].read_text(encoding="utf-8").split()) if paths["dev"].exists() else set()
    test_ids = set(paths["test"].read_text(encoding="utf-8").split()) if paths["test"].exists() else set()
    sheet_by_item = defaultdict(list)
    for r in sheet:
        sheet_by_item[r["item_id"]].append(r)

    issues = []

    def add(item, sev, code, detail):
        issues.append({"item_id": item, "severity": sev, "code": code, "detail": detail})

    # --- kiểm tra mức tệp
    ids = [r["item_id"] for r in gold]
    for i, c in Counter(ids).items():
        if c > 1:
            add(i, "ERROR", "duplicate_item_id", f"item_id xuất hiện {c} lần trong gold_summaries.csv")
    if dev_ids & test_ids:
        add("*", "ERROR", "split_overlap", f"ID nằm ở cả dev và test: {sorted(dev_ids & test_ids)}")
    if not paths["sheet"].exists():
        add("*", "WARN", "no_numeric_sheet", "chưa có data/annotations/gold_numeric_facts.csv")
    if gold and "draft_source" not in gold[0]:
        add("*", "WARN", "no_draft_source_col", "gold_summaries.csv chưa có cột draft_source (human/llm_edited)")

    stats = Counter()
    versions = Counter()
    test_before_lock = []

    for r in gold:
        iid = r["item_id"]
        if a.items and iid not in a.items:
            continue
        status = r.get("review_status", "").strip()
        summ = r.get("reference_summary", "").strip()
        split = r.get("split", "")
        stats[(split, status or "(trống)")] += 1

        if iid not in arts:
            add(iid, "ERROR", "article_missing", "không có bài trong selected_articles.jsonl")
            continue
        if status not in STATUSES:
            add(iid, "ERROR", "bad_status", f"review_status='{status}' không hợp lệ ({sorted(STATUSES)})")
        exp_split = "dev" if iid in dev_ids else "test" if iid in test_ids else None
        if exp_split and split != exp_split:
            add(iid, "ERROR", "split_mismatch", f"gold ghi split='{split}' nhưng danh sách ID khóa là '{exp_split}'")
        if status == "exclude":
            if iid not in log_ids:
                add(iid, "WARN", "exclude_no_log", "bài bị loại nhưng chưa có dòng lý do trong review_log.csv")
            continue
        if status == "todo" and not summ:
            continue
        if not summ:
            add(iid, "ERROR", "empty_summary", f"status='{status}' nhưng reference_summary trống")
            continue

        # --- metadata
        annot, rev = r.get("annotator_id", "").strip(), r.get("reviewer_id", "").strip()
        ver = r.get("guideline_version", "").strip()
        versions[ver or "(trống)"] += 1
        if not annot:
            add(iid, "ERROR", "no_annotator", "thiếu annotator_id")
        if not ver:
            add(iid, "ERROR", "no_version", "thiếu guideline_version")
        if rev and rev == annot:
            add(iid, "ERROR", "self_review", "người rà soát trùng người gắn nhãn")
        if status == "reviewed":
            if not rev:
                add(iid, "ERROR", "reviewed_no_reviewer", "status=reviewed nhưng chưa có reviewer_id")
            if iid not in log_ids:
                add(iid, "WARN", "reviewed_no_log", "chưa có dòng trong review_log.csv")
        if "draft_source" in r and r["draft_source"].strip() not in DRAFT_SOURCES:
            add(iid, "WARN", "draft_source", f"draft_source='{r['draft_source']}' (cần {sorted(DRAFT_SOURCES)})")
        if split == "test":
            if a.locked_version:
                lv, vv = vtuple(a.locked_version), vtuple(ver)
                if vv is None or vv < lv:
                    add(iid, "ERROR", "version_before_lock",
                        f"bài test có guideline_version='{ver}' < bản đã khóa {a.locked_version}")
            else:
                test_before_lock.append(iid)
        elif split == "dev" and a.locked_version:
            vv, lv = vtuple(ver), vtuple(a.locked_version)
            if vv is None or vv < lv:
                add(iid, "WARN", "dev_old_version", f"bài dev viết theo '{ver}', cần rà lại theo {a.locked_version}")

        # --- hình thức tóm tắt
        sents = split_sentences(summ)
        nw = len(summ.split())
        if not (a.min_sent <= len(sents) <= a.max_sent):
            add(iid, "ERROR", "sentence_count",
                f"{len(sents)} câu (cần {a.min_sent}-{a.max_sent}); đếm bằng heuristic, xem lại tay nếu có viết tắt")
        if not (a.min_words <= nw <= a.max_words):
            add(iid, "WARN", "word_count", f"{nw} từ (khuyến nghị {a.min_words}-{a.max_words})")
        if BULLET_RE.search(summ):
            add(iid, "ERROR", "bullets", "tóm tắt có gạch đầu dòng/tiêu đề; cần văn xuôi")
        elif "\n" in summ:
            add(iid, "WARN", "newline", "tóm tắt xuống dòng; nên là một đoạn văn xuôi")
        desc = r.get("description_ref_NOT_GOLD", "").strip()
        if desc and difflib.SequenceMatcher(None, norm_text(desc), norm_text(summ)).ratio() >= 0.9:
            add(iid, "WARN", "copied_description", "tóm tắt gần như trùng description; đã đối chiếu với thân bài chưa?")

        # --- số liệu: tóm tắt so với thân bài
        article = arts[iid]["content"]
        A, S = analyze(article), analyze(summ)
        art_raw = set(A["tokens"]) | {v for v, _ in A["facts"]}
        art_float = (
            {to_float(x) for x in A["tokens"]}
            | {to_float(v) for v, _ in A["facts"]}
            | {to_float(d) for d, _ in A["dotdec"]}
        )
        art_dot_raw = {d for d, _ in A["dotdec"]}
        art_fact = defaultdict(set)
        for v, u in A["facts"]:
            art_fact[to_float(v)].add(u)
        for d, u in A["dotdec"]:
            if u:
                art_fact[to_float(d)].add(u)

        for tok in S["tokens"]:
            if tok in art_raw:
                continue
            if to_float(tok) in art_float:
                add(iid, "WARN", "number_format_differs",
                    f"'{tok}' cùng giá trị với số trong bài nhưng viết khác (guideline: giữ cách viết của bài)")
            else:
                add(iid, "ERROR", "number_not_in_article", f"'{tok}' không có trong thân bài (bịa/tự tính/lấy từ tiêu đề?)")

        for v, u in S["facts"]:
            f = to_float(v)
            if f not in art_fact:
                continue  # đã báo ở number_not_in_article hoặc number_format_differs
            units = art_fact[f]
            if u in units:
                continue
            if any(unit_related(u, x) for x in units):
                add(iid, "WARN", "unit_shortened", f"'{v} {u}': bài viết đơn vị là {sorted(units)}")
            else:
                add(iid, "ERROR", "unit_mismatch", f"'{v} {u}': trong bài số này đi với đơn vị {sorted(units)}")
        for v, u in S["facts"]:
            f = to_float(v)
            if f not in art_fact and f in art_float:
                add(iid, "REVIEW", "unit_unverifiable", f"'{v} {u}': bài có số này nhưng máy không gắn được đơn vị; xem tay")

        for d, u in S["dotdec"]:
            f = to_float(d)
            in_lit = d in art_dot_raw
            comma_form = f in {to_float(x) for x in A["tokens"]}
            if not in_lit and f not in art_float:
                add(iid, "ERROR", "number_not_in_article", f"'{d}{u}' không có trong thân bài")
            add(iid, "REVIEW", "dot_decimal",
                f"'{d}{u}' dùng dấu chấm thập phân. Trong bài: nguyên văn={'có' if in_lit else 'không'}, "
                f"dạng dấu phẩy cùng giá trị={'có' if comma_form else 'không'}. Máy không xác nhận được ý nghĩa; "
                "người xem lại (có phải 3,2 hay định dạng khác).")
        if A["dotdec"] and not S["dotdec"]:
            add(iid, "REVIEW", "article_dot_decimal",
                f"thân bài có số dạng chấm thập phân {sorted({d for d, _ in A['dotdec']})[:5]}; kiểm tra tóm tắt/phiếu không bị đổi nghĩa")

        art_periods = set(A["periods"])
        for p in S["periods"]:
            if p not in art_periods:
                add(iid, "WARN", "period_not_in_article", f"mốc '{p}' không xuất hiện nguyên dạng trong bài; kiểm tra tay kỳ/năm")

        # --- phiếu số liệu
        rows = sheet_by_item.get(iid, [])
        keys, floats, seen_fid = set(), set(), set()
        art_norm = norm_text(article)
        for row in rows:
            fid = row.get("fact_id", "").strip()
            if fid in seen_fid:
                add(iid, "ERROR", "dup_fact_id", f"fact_id '{fid}' trùng")
            seen_fid.add(fid)
            miss = [c for c in SHEET_REQUIRED if not row.get(c, "").strip()]
            if miss:
                add(iid, "ERROR", "sheet_missing_field", f"{fid}: thiếu {miss}")
            if row.get("modality", "").strip() and row["modality"].strip() not in MODALITIES:
                add(iid, "ERROR", "sheet_modality", f"{fid}: modality='{row['modality']}' (cần {sorted(MODALITIES)})")
            if not row.get("unit", "").strip():
                add(iid, "WARN", "sheet_no_unit", f"{fid}: để trống unit (đúng nếu là số đếm không đơn vị)")
            try:
                f = to_float(row["value"])
            except (ValueError, KeyError):
                add(iid, "ERROR", "sheet_bad_value", f"{fid}: value='{row.get('value')}' không phải số")
                continue
            keys.add((f, unorm(row.get("unit", ""))))
            floats.add(f)
            src = norm_text(row.get("source_sentence", ""))
            if src:
                if src not in art_norm:
                    add(iid, "ERROR", "source_not_in_article", f"{fid}: source_sentence không có nguyên văn trong bài")
                if row["value"].strip() not in src:
                    add(iid, "ERROR", "value_not_in_source", f"{fid}: giá trị '{row['value']}' không nằm trong source_sentence")

        def has_key(f, u):
            return any(f == kf and (u == ku or unit_related(u, ku)) for kf, ku in keys)

        for v, u in S["facts"]:
            if not has_key(to_float(v), u):
                add(iid, "ERROR", "missing_fact_row", f"'{v} {u}' có trong tóm tắt nhưng chưa có dòng trong gold_numeric_facts.csv")
        for d, u in S["dotdec"]:
            if not has_key(to_float(d), u):
                add(iid, "ERROR", "missing_fact_row", f"'{d}{u}' có trong tóm tắt nhưng chưa có dòng trong phiếu")
        period_numbers = {to_float(n) for p in S["periods"] for n in re.findall(NUM, p)}
        sum_floats = (
            {to_float(x) for x in S["tokens"]}
            | {to_float(x) for x, _ in S["facts"]}
            | {to_float(d) for d, _ in S["dotdec"]}
            | period_numbers
        )
        for tok in S["bare"]:
            if to_float(tok) not in floats:
                add(iid, "WARN", "bare_number_not_in_sheet",
                    f"'{tok}' (không đơn vị) không có trong phiếu; nếu là số liệu thì thêm dòng, nếu là năm/ngày thì bỏ qua")
        for row in rows:
            try:
                if to_float(row["value"]) not in sum_floats:
                    add(iid, "WARN", "orphan_sheet_row", f"{row.get('fact_id', '')}: giá trị '{row['value']}' không có trong tóm tắt")
            except (ValueError, KeyError):
                pass
        if not arts[iid].get("has_numbers", True) and (S["tokens"] or S["dotdec"]):
            add(iid, "REVIEW", "low_number_article_has_numbers",
                "bài ít số liệu nhưng tóm tắt có số: xác nhận từng số có trong bài (nhóm này dùng đo việc bịa số)")

    if test_before_lock:
        add("*", "WARN", "test_written_before_lock",
            f"{len(test_before_lock)} bài test đã có tóm tắt nhưng chưa khai báo --locked-version "
            f"(guideline v1.0 chưa khóa?). Ví dụ: {test_before_lock[:5]}")

    # ------------------------------------------------------------------------- báo cáo
    out_dir = root / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(issues, columns=["item_id", "severity", "code", "detail"])
    order = {"ERROR": 0, "REVIEW": 1, "WARN": 2}
    if len(df):
        df = df.sort_values(by=["severity", "item_id", "code"], key=lambda c: c.map(order) if c.name == "severity" else c)
    df.to_csv(out_dir / "gold_check_issues.csv", index=False, encoding="utf-8-sig")
    sev = Counter(df["severity"]) if len(df) else Counter()

    n_cross = sum(1 for r in gold if r.get("cross_review_required", "") == "True"
                  and r.get("review_status") in {"annotated", "reviewed"})
    n_done = sum(1 for r in gold if r.get("review_status") == "reviewed")
    n_written = sum(v for (sp, st), v in stats.items() if st in {"annotated", "reviewed"})
    L = ["# Báo cáo tự kiểm gold (tự sinh bởi src/check_gold.py)", "",
         "> **Giới hạn:** script chỉ so khớp chuỗi/số với thân bài. Nó không xác nhận được chủ thể, kỳ/cơ sở so sánh, "
         "dự báo hay thực tế, ý chính, hay ý nghĩa của số dạng `3.2%`. Không có ERROR **không có nghĩa** gold đúng; "
         "mọi mục REVIEW và các bài được rà soát chéo vẫn phải do người kiểm.", "",
         f"- Guideline đã khóa: {a.locked_version or 'CHƯA khai báo'}",
         f"- Phiên bản guideline đang dùng trong gold: {dict(versions) or 'chưa có bài nào'}", "",
         "## Tiến độ", "", "| Split | Trạng thái | Số bài |", "|---|---|---:|"]
    L += [f"| {sp or '(trống)'} | {st} | {v} |" for (sp, st), v in sorted(stats.items())]
    L += ["", f"- Đã viết (annotated/reviewed): {n_written} | đã rà soát chéo (reviewed): {n_done} "
          f"({(n_done / n_written if n_written else 0):.0%}; yêu cầu >= 20%)",
          f"- Bài đánh dấu cần hậu kiểm chéo đã viết xong: {n_cross}", "",
          "## Tổng hợp", "", f"- ERROR: {sev['ERROR']} | REVIEW: {sev['REVIEW']} | WARN: {sev['WARN']}", ""]
    if len(df):
        L += ["| Mức | Bài | Mã | Chi tiết |", "|---|---|---|---|"]
        L += [f"| {r.severity} | {r.item_id} | {r.code} | {str(r.detail).replace('|', '/')} |" for r in df.itertuples()]
    else:
        L.append("Không có vấn đề nào được ghi nhận (kể cả khi chưa có bài nào được viết).")
    (out_dir / "gold_check_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"Đã viết {n_written} bài | ERROR {sev['ERROR']} | REVIEW {sev['REVIEW']} | WARN {sev['WARN']}")
    for r in df.head(30).itertuples():
        print(f"[{r.severity}] {r.item_id} {r.code}: {r.detail}")
    if len(df) > 30:
        print(f"... còn {len(df) - 30} dòng, xem reports/gold_check_issues.csv")
    print("Chi tiết: reports/gold_check_report.md")
    print("Nhắc: script không xác nhận được ý nghĩa/độ đúng của dữ kiện; mục REVIEW cần người xem.")
    sys.exit(1 if sev["ERROR"] or (a.strict and sev["WARN"]) else 0)


if __name__ == "__main__":
    main()
