#!/usr/bin/env python3
"""Export candidate error cases across E0/E1/E2 predictions for error_analysis.md."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

from check_gold import split_sentences
from evaluate import write_csv_atomic

CANDIDATE_COLUMNS = [
    "item_id",
    "split",
    "experiments_present",
    "error_flags",
    "rougeL_by_exp",
    "word_count_by_exp",
    "surface_not_found_by_exp",
    "gold_fact_recall_by_exp",
    "gold_fact_count",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--rouge-threshold", type=float, default=0.25)
    args = parser.parse_args()

    root = args.root.resolve()
    reports_dir = root / "reports"
    pred_files = sorted(reports_dir.glob(f"{args.split}_predictions_E*.csv"))
    if not pred_files:
        raise SystemExit(f"No prediction files found for split={args.split}")

    by_item: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for pred_file in pred_files:
        with pred_file.open(encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                exp = row["experiment"].strip()
                by_item[row["item_id"].strip()][exp] = row

    out_rows: list[dict[str, Any]] = []
    for item_id in sorted(by_item):
        exp_map = by_item[item_id]
        flags: list[str] = []
        rouge_parts: list[str] = []
        wc_parts: list[str] = []
        nf_parts: list[str] = []
        rec_parts: list[str] = []
        gold_count = "0"

        for exp in sorted(exp_map):
            r = exp_map[exp]
            gold_count = r.get("gold_fact_count", "0")
            summary = (r.get("summary_after_postcheck") or r.get("summary_before_postcheck") or "").strip()
            wc = len(summary.split())
            sc = len(split_sentences(summary)) if summary else 0
            rl = float(r["rougeL_f1_after"]) if r.get("rougeL_f1_after") else 0.0
            nf = int(r.get("source_value_not_found_after") or 0)
            rec = r.get("gold_fact_surface_recall_after", "")
            rouge_parts.append(f"{exp}:{rl:.4f}")
            wc_parts.append(f"{exp}:{wc}w/{sc}s")
            nf_parts.append(f"{exp}:{nf}")
            rec_parts.append(f"{exp}:{rec or 'N/A'}")

            if rl < args.rouge_threshold:
                flags.append(f"{exp}_low_rougeL")
            if wc < 50 or wc > 120:
                flags.append(f"{exp}_length_out_of_range")
            if sc < 3 or sc > 5:
                flags.append(f"{exp}_sentence_count_out_of_range")
            if nf > 0:
                flags.append(f"{exp}_surface_not_found")
            if int(gold_count or 0) > 0 and rec and float(rec) == 0.0:
                flags.append(f"{exp}_zero_gold_fact_recall")
            if r.get("factuality_score", "").strip() in {"0", "1"}:
                flags.append(f"{exp}_human_factuality_{r['factuality_score'].strip()}")

        if flags:
            out_rows.append(
                {
                    "item_id": item_id,
                    "split": args.split,
                    "experiments_present": ",".join(sorted(exp_map)),
                    "error_flags": ";".join(flags),
                    "rougeL_by_exp": " | ".join(rouge_parts),
                    "word_count_by_exp": " | ".join(wc_parts),
                    "surface_not_found_by_exp": " | ".join(nf_parts),
                    "gold_fact_recall_by_exp": " | ".join(rec_parts),
                    "gold_fact_count": gold_count,
                }
            )

    out_path = reports_dir / f"error_candidates_{args.split}.csv"
    write_csv_atomic(out_path, CANDIDATE_COLUMNS, out_rows)
    print(f"Wrote {len(out_rows)} candidate error items to {out_path}")


if __name__ == "__main__":
    main()
