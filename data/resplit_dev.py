#!/usr/bin/env python3
"""
Chia lại dev cho ĐT05, giữ nguyên 60 bài đã chọn bởi prepare_data.py (chỉ đổi cột split).

Quy tắc dev (10 bài mặc định):
  1. Mỗi chủ đề có trong mẫu có >= 1 bài dev (8 chủ đề -> 8 bài).
  2. Có >= 2 bài ít số liệu (has_numbers=False), ưu tiên lấy từ chủ đề ít rủi ro số liệu.
  3. Chỗ dư còn lại: ưu tiên thêm 1 bài `doanh_nghiep` (loại tin dễ sai số liệu nhất), rồi ngẫu nhiên.

Chống leakage: prepare_data.py đã đảm bảo mọi cặp bài trong 60 bài có cosine < event-sim,
nên bất kỳ cách chia nào cũng không đưa hai bài cùng sự kiện sang hai split khác nhau.

Chạy:
    python src/resplit_dev.py --dry-run     # xem trước, không ghi gì
    python src/resplit_dev.py               # ghi thật
Script từ chối chạy nếu đã có reference_summary được điền (đang gắn nhãn), trừ khi --force.
"""
import argparse
import json
import random
from datetime import datetime
from pathlib import Path

import pandas as pd

LOW_RISK_ORDER = ["khac", "bat_dong_san", "hang_hoa", "xuat_nhap_khau",
                  "tien_te_ngan_hang", "chung_khoan", "vi_mo", "doanh_nghiep"]


def parse_notes(s):
    return dict(kv.split("=", 1) for kv in str(s).split(";") if "=" in kv)


def choose_dev(df, n_dev, min_low, rng):
    topics = sorted(df["topic"].unique(), key=lambda t: LOW_RISK_ORDER.index(t) if t in LOW_RISK_ORDER else 99)
    if n_dev < len(topics):
        raise SystemExit(f"n_dev={n_dev} < số chủ đề={len(topics)}; không thể mỗi chủ đề 1 bài.")
    chosen = {}
    low_needed = min_low
    # Bước 1: lấy bài ít số liệu từ các chủ đề ít rủi ro trước
    for t in topics:
        if low_needed == 0:
            break
        pool = df[(df.topic == t) & (~df.has_numbers)]
        if len(pool):
            chosen[t] = [rng.choice(pool.item_id.tolist())]
            low_needed -= 1
    if low_needed > 0:
        raise SystemExit(f"Chỉ tìm đủ {min_low - low_needed}/{min_low} bài ít số liệu ở các chủ đề khác nhau; "
                         "hãy giảm --min-low.")
    # Bước 2: chủ đề chưa có đại diện lấy 1 bài nhiều số liệu
    for t in topics:
        if t not in chosen:
            pool = df[(df.topic == t) & (df.has_numbers)]
            if not len(pool):
                pool = df[df.topic == t]
            chosen[t] = [rng.choice(pool.item_id.tolist())]
    picked = [i for v in chosen.values() for i in v]
    # Bước 3: chỗ dư — ưu tiên doanh_nghiep (nhiều số liệu), rồi ngẫu nhiên
    extra = n_dev - len(picked)
    if extra > 0 and "doanh_nghiep" in topics:
        pool = df[(df.topic == "doanh_nghiep") & (df.has_numbers) & (~df.item_id.isin(picked))]
        if len(pool):
            picked.append(rng.choice(pool.item_id.tolist()))
            extra -= 1
    if extra > 0:
        pool = df[(df.has_numbers) & (~df.item_id.isin(picked))].item_id.tolist()
        picked += rng.sample(pool, extra)
    return picked


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default=".")
    p.add_argument("--n-dev", type=int, default=10)
    p.add_argument("--min-low", type=int, default=2)
    p.add_argument("--min-test", type=int, default=40)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    root = Path(a.root)
    man_path = root / "data/data_manifest.csv"
    gold_path = root / "data/annotations/gold_summaries.csv"

    man = pd.read_csv(man_path, encoding="utf-8-sig", dtype=str)
    meta = man["notes"].map(parse_notes)
    df = pd.DataFrame({
        "item_id": man["item_id"],
        "old_split": man["split"],
        "topic": meta.map(lambda d: d.get("topic", "khac")),
        "has_numbers": meta.map(lambda d: d.get("has_numbers", "False") == "True"),
    })

    if gold_path.exists() and not a.force:
        g = pd.read_csv(gold_path, encoding="utf-8-sig", dtype=str).fillna("")
        if (g["reference_summary"].str.strip() != "").any():
            raise SystemExit("Đã có reference_summary được điền: ĐỪNG đổi split sau khi bắt đầu gắn nhãn. "
                             "Nếu thật sự cần, chạy lại với --force và ghi lý do vào review_log.")

    rng = random.Random(a.seed)
    dev_ids = set(choose_dev(df, a.n_dev, a.min_low, rng))
    df["new_split"] = df["item_id"].map(lambda i: "dev" if i in dev_ids else "test")

    n_test = int((df.new_split == "test").sum())
    assert (df.new_split == "dev").sum() == a.n_dev, "Số bài dev không đúng"
    assert n_test >= a.min_test, f"Test chỉ có {n_test} bài (< {a.min_test})"
    assert set(df.topic.unique()) <= set(df[df.new_split == "dev"].topic.unique()), "Dev thiếu chủ đề"

    print("== Dev mới ==")
    print(df[df.new_split == "dev"].groupby(["topic", "has_numbers"]).size().unstack(fill_value=0))
    print(f"\nDev: {a.n_dev} (ít số liệu: {int((~df[df.new_split == 'dev'].has_numbers).sum())}) | Test: {n_test}")
    print("Thay đổi so với split cũ:", int((df.old_split != df.new_split).sum()), "bài đổi split")
    if a.dry_run:
        print("\n[dry-run] Chưa ghi gì.")
        return

    # Ghi: manifest, gold template, jsonl, danh sách ID, lịch sử
    new_split = dict(zip(df.item_id, df.new_split))
    man["split"] = man["item_id"].map(new_split)
    man.to_csv(man_path, index=False, encoding="utf-8-sig")

    if gold_path.exists():
        g = pd.read_csv(gold_path, encoding="utf-8-sig", dtype=str).fillna("")
        g["split"] = g["item_id"].map(new_split)
        g.to_csv(gold_path, index=False, encoding="utf-8-sig")

    jl = root / "data/processed/selected_articles.jsonl"
    if jl.exists():
        rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
        for r in rows:
            r["split"] = new_split[r["item_id"]]
        jl.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    sp = root / "data/splits"
    sp.mkdir(parents=True, exist_ok=True)
    (sp / "dev_ids.txt").write_text("\n".join(sorted(dev_ids)) + "\n", encoding="utf-8")
    (sp / "test_ids.txt").write_text("\n".join(sorted(df[df.new_split == "test"].item_id)) + "\n", encoding="utf-8")
    hist = sp / "split_history.json"
    log = json.loads(hist.read_text(encoding="utf-8")) if hist.exists() else []
    log.append({"time": datetime.now().isoformat(timespec="seconds"), "seed": a.seed, "n_dev": a.n_dev,
                "min_low": a.min_low, "reason": "dev phủ đủ chủ đề; đổi trước khi gắn nhãn",
                "old_dev": sorted(df[df.old_split == "dev"].item_id), "new_dev": sorted(dev_ids)})
    hist.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nĐã ghi. Lịch sử đổi split: data/splits/split_history.json")
    print("Việc tiếp theo: commit/khóa dev_ids.txt và test_ids.txt TRƯỚC khi bắt đầu gắn nhãn.")


if __name__ == "__main__":
    main()
