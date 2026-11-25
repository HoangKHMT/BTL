#!/usr/bin/env python3
"""Aggregate experiments.csv and optional human_eval_sheet.csv into metrics_summary.csv."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from evaluate import write_csv_atomic

SUMMARY_COLUMNS = [
    "experiment",
    "split",
    "method",
    "model_id",
    "prompt_version",
    "temperature",
    "postcheck_policy",
    "sample_count",
    "rouge1_f1_before_macro",
    "rouge2_f1_before_macro",
    "rougeL_f1_before_macro",
    "rouge1_f1_after_macro",
    "rouge2_f1_after_macro",
    "rougeL_f1_after_macro",
    "numeric_claims_before",
    "exact_value_unit_matches_before",
    "exact_value_unit_match_rate_before",
    "numeric_claims_after",
    "exact_value_unit_matches_after",
    "exact_value_unit_match_rate_after",
    "gold_fact_surface_recall_before_macro",
    "gold_fact_surface_recall_after_macro",
    "human_reviewed_items",
    "human_numeric_precision",
    "human_numeric_hallucination_rate",
    "human_factuality_mean",
    "human_factuality_0_count",
    "human_factuality_1_count",
    "human_factuality_2_count",
    "run_id",
    "run_label",
    "run_commit",
    "status",
]


def load_human_summary(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    if not path.exists():
        return {}
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("human_review_status", "").strip() != "reviewed":
                continue
            key = (
                row.get("experiment", "").strip(),
                row.get("split", "").strip(),
                row.get("run_label", "").strip(),
            )
            grouped[key].append(row)

    stats: dict[tuple[str, str, str], dict[str, Any]] = {}
    for key, items in grouped.items():
        sup_total = sum(int(x["supported_claims"]) for x in items if x.get("supported_claims", "").strip() != "")
        unsup_total = sum(int(x["unsupported_claims"]) for x in items if x.get("unsupported_claims", "").strip() != "")
        contra_total = sum(int(x["contradicted_claims"]) for x in items if x.get("contradicted_claims", "").strip() != "")
        denom = sup_total + unsup_total + contra_total
        fact_scores = [int(x["factuality_score"]) for x in items if x.get("factuality_score", "").strip() in {"0", "1", "2"}]
        stats[key] = {
            "human_reviewed_items": len(items),
            "human_numeric_precision": f"{sup_total / denom:.6f}" if denom else "N/A (0 claims)",
            "human_numeric_hallucination_rate": f"{(unsup_total + contra_total) / denom:.6f}" if denom else "N/A (0 claims)",
            "human_factuality_mean": f"{mean(fact_scores):.4f}" if fact_scores else "",
            "human_factuality_0_count": sum(s == 0 for s in fact_scores),
            "human_factuality_1_count": sum(s == 1 for s in fact_scores),
            "human_factuality_2_count": sum(s == 2 for s in fact_scores),
        }
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--all-runs", action="store_true", help="Keep all completed runs instead of latest per (experiment, split)")
    args = parser.parse_args()

    root = args.root.resolve()
    exp_path = root / "reports/experiments.csv"
    if not exp_path.exists():
        raise SystemExit(f"experiments.csv not found: {exp_path}")

    with exp_path.open(encoding="utf-8-sig", newline="") as file:
        runs = [r for r in csv.DictReader(file) if r.get("status") == "completed"]

    if not args.all_runs:
        latest: dict[tuple[str, str], dict[str, str]] = {}
        for run in runs:
            latest[(run.get("experiment", ""), run.get("split", ""))] = run
        runs = sorted(latest.values(), key=lambda r: (r.get("split", ""), r.get("experiment", "")))

    human_stats = load_human_summary(root / "reports/human_eval_sheet.csv")
    summary_rows: list[dict[str, Any]] = []
    for run in runs:
        key = (run.get("experiment", ""), run.get("split", ""), run.get("run_label", ""))
        h = human_stats.get(key, {})
        summary_rows.append(
            {
                **{col: run.get(col, "") for col in SUMMARY_COLUMNS if col in run},
                "human_reviewed_items": h.get("human_reviewed_items", 0),
                "human_numeric_precision": h.get("human_numeric_precision", ""),
                "human_numeric_hallucination_rate": h.get("human_numeric_hallucination_rate", ""),
                "human_factuality_mean": h.get("human_factuality_mean", ""),
                "human_factuality_0_count": h.get("human_factuality_0_count", ""),
                "human_factuality_1_count": h.get("human_factuality_1_count", ""),
                "human_factuality_2_count": h.get("human_factuality_2_count", ""),
            }
        )

    out_path = root / "reports/metrics_summary.csv"
    write_csv_atomic(out_path, SUMMARY_COLUMNS, summary_rows)
    print(f"Wrote {len(summary_rows)} summary row(s) to {out_path}")


if __name__ == "__main__":
    main()
