#!/usr/bin/env python3
"""Build and recompute human evaluation sheets and numeric error tables for DT05."""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path
from typing import Any

from check_gold import analyze, split_sentences, to_float
from evaluate import load_articles, numeric_claims, source_surface_status, write_csv_atomic

HUMAN_EVAL_COLUMNS = [
    "eval_id",
    "item_id",
    "split",
    "experiment",
    "run_label",
    "model_id",
    "summary_to_review",
    "reference_summary",
    "word_count",
    "sentence_count",
    "length_in_50_120",
    "sentences_in_3_5",
    "rougeL_f1_after",
    "auto_numeric_claims",
    "auto_exact_value_unit_matches",
    "auto_surface_not_found",
    "gold_fact_count",
    "auto_gold_facts_matched",
    "supported_claims",
    "unsupported_claims",
    "contradicted_claims",
    "supported_gold_facts_reproduced",
    "numeric_precision",
    "numeric_hallucination_rate",
    "gold_numeric_recall",
    "factuality_score",
    "readability_score",
    "human_review_status",
    "reviewer_id",
    "reviewer_note",
]

NUMERIC_ERROR_COLUMNS = [
    "item_id",
    "split",
    "experiment",
    "run_label",
    "stage",
    "claim_type",
    "raw",
    "value",
    "unit",
    "source_surface_status",
    "matching_source_sentences",
    "human_verdict",
    "reviewer_id",
    "reviewer_note",
]

BLIND_KEY_COLUMNS = ["eval_id", "item_id", "split", "experiment", "run_label", "model_id"]


def matching_sentences_for_value(value_str: str, article_content: str) -> str:
    """Return source sentences containing the claim's numeric value (exact or float match)."""
    sents = split_sentences(article_content)
    try:
        target = to_float(value_str)
    except ValueError:
        target = None

    matches: list[str] = []
    for sent in sents:
        if value_str and value_str in sent:
            matches.append(sent)
            continue
        if target is not None:
            parsed = analyze(sent)
            sent_vals = (
                {to_float(x) for x in parsed["tokens"]}
                | {to_float(x) for x, _ in parsed["facts"]}
                | {to_float(x) for x, _ in parsed["dotdec"]}
            )
            if target in sent_vals:
                matches.append(sent)
    return " | ".join(matches[:3])


def parse_pred_filename(path: Path, split: str) -> tuple[str, str]:
    pattern = re.compile(rf"^{re.escape(split)}_predictions_(E0|E1|E2)(?:_(.+))?\.csv$")
    match = pattern.match(path.name)
    if not match:
        raise ValueError(f"Cannot parse experiment/run_label from {path.name}")
    return match.group(1), match.group(2) or ""


def load_existing_rows(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    if not path.exists():
        return {}
    existing: dict[tuple[str, str, str], dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key = (
                row.get("item_id", "").strip(),
                row.get("experiment", "").strip(),
                row.get("run_label", "").strip(),
            )
            if key[0] and key[1]:
                existing[key] = row
    return existing


def recompute_row_metrics(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    sup_raw = updated.get("supported_claims", "").strip()
    unsup_raw = updated.get("unsupported_claims", "").strip()
    contra_raw = updated.get("contradicted_claims", "").strip()
    if sup_raw != "" and unsup_raw != "" and contra_raw != "":
        sup = int(sup_raw)
        unsup = int(unsup_raw)
        contra = int(contra_raw)
        total = sup + unsup + contra
        if total == 0:
            updated["numeric_precision"] = "N/A (0 claims)"
            updated["numeric_hallucination_rate"] = "N/A (0 claims)"
        else:
            updated["numeric_precision"] = f"{sup / total:.6f}"
            updated["numeric_hallucination_rate"] = f"{(unsup + contra) / total:.6f}"
    gold_repro_raw = updated.get("supported_gold_facts_reproduced", "").strip()
    gold_total_raw = updated.get("gold_fact_count", "").strip()
    if gold_repro_raw != "" and gold_total_raw != "":
        gold_total = int(gold_total_raw)
        if gold_total == 0:
            updated["gold_numeric_recall"] = "N/A (0 gold facts)"
        else:
            updated["gold_numeric_recall"] = f"{int(gold_repro_raw) / gold_total:.6f}"
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--blind", action="store_true", help="Assign randomized blind eval_id and export separate key")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--include-all-claims", action="store_true", help="Include value_unit_match claims in numeric_error_table.csv")
    parser.add_argument("--recompute-only", action="store_true", help="Recompute derived rates in existing human_eval_sheet.csv")
    args = parser.parse_args()

    root = args.root.resolve()
    reports_dir = root / "reports"
    sheet_path = reports_dir / f"human_eval_sheet_{args.split}.csv"
    if args.split == "dev" and not sheet_path.exists() and (reports_dir / "human_eval_sheet.csv").exists():
        sheet_path = reports_dir / "human_eval_sheet.csv"
    default_sheet = reports_dir / "human_eval_sheet.csv"

    if args.recompute_only:
        target = sheet_path if sheet_path.exists() else default_sheet
        if not target.exists():
            raise SystemExit(f"Human eval sheet not found: {target}")
        with target.open(encoding="utf-8-sig", newline="") as file:
            rows = [recompute_row_metrics(row) for row in csv.DictReader(file)]
        write_csv_atomic(target, HUMAN_EVAL_COLUMNS, rows)
        print(f"Recomputed {len(rows)} rows in {target}")
        return

    articles_path = root / "data/processed/selected_articles.jsonl"
    if not articles_path.exists():
        raise SystemExit(f"Required articles file not found: {articles_path}")
    articles = load_articles(articles_path, args.split)

    pred_files = sorted(reports_dir.glob(f"{args.split}_predictions_E*.csv"))
    if not pred_files:
        raise SystemExit(f"No prediction files found matching {reports_dir}/{args.split}_predictions_E*.csv")

    existing = load_existing_rows(default_sheet)
    rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    for pred_file in pred_files:
        exp, run_label = parse_pred_filename(pred_file, args.split)
        with pred_file.open(encoding="utf-8-sig", newline="") as file:
            for prow in csv.DictReader(file):
                item_id = prow["item_id"].strip()
                summary = (prow.get("summary_after_postcheck") or prow.get("summary_before_postcheck") or "").strip()
                words = len(summary.split())
                sents = len(split_sentences(summary)) if summary else 0
                prev = existing.get((item_id, exp, run_label), {})
                row = {
                    "eval_id": prev.get("eval_id", f"{args.split}-{exp}-{item_id}"),
                    "item_id": item_id,
                    "split": args.split,
                    "experiment": exp,
                    "run_label": run_label,
                    "model_id": prow.get("model_id", ""),
                    "summary_to_review": summary,
                    "reference_summary": prow.get("reference_summary", ""),
                    "word_count": words,
                    "sentence_count": sents,
                    "length_in_50_120": 50 <= words <= 120,
                    "sentences_in_3_5": 3 <= sents <= 5,
                    "rougeL_f1_after": prow.get("rougeL_f1_after", ""),
                    "auto_numeric_claims": prow.get("numeric_claims_after", "0"),
                    "auto_exact_value_unit_matches": prow.get("exact_value_unit_matches_after", "0"),
                    "auto_surface_not_found": prow.get("source_value_not_found_after", "0"),
                    "gold_fact_count": prow.get("gold_fact_count", "0"),
                    "auto_gold_facts_matched": prow.get("gold_facts_matched_after", "0"),
                    "supported_claims": prev.get("supported_claims", prow.get("supported_claims", "")),
                    "unsupported_claims": prev.get("unsupported_claims", prow.get("unsupported_claims", "")),
                    "contradicted_claims": prev.get("contradicted_claims", prow.get("contradicted_claims", "")),
                    "supported_gold_facts_reproduced": prev.get("supported_gold_facts_reproduced", ""),
                    "numeric_precision": prev.get("numeric_precision", prow.get("numeric_precision", "")),
                    "numeric_hallucination_rate": prev.get("numeric_hallucination_rate", prow.get("numeric_hallucination_rate", "")),
                    "gold_numeric_recall": prev.get("gold_numeric_recall", prow.get("gold_numeric_recall", "")),
                    "factuality_score": prev.get("factuality_score", prow.get("factuality_score", "")),
                    "readability_score": prev.get("readability_score", ""),
                    "human_review_status": prev.get("human_review_status", prow.get("human_review_status", "pending")),
                    "reviewer_id": prev.get("reviewer_id", ""),
                    "reviewer_note": prev.get("reviewer_note", prow.get("reviewer_note", "")),
                }
                rows.append(recompute_row_metrics(row))

                article = articles.get(item_id)
                if article and summary:
                    source_analysis = analyze(article["content"])
                    for claim in numeric_claims(summary):
                        status = source_surface_status(claim, source_analysis)
                        if not args.include_all_claims and status == "value_unit_match":
                            continue
                        error_rows.append(
                            {
                                "item_id": item_id,
                                "split": args.split,
                                "experiment": exp,
                                "run_label": run_label,
                                "stage": "after_postcheck",
                                "claim_type": claim["claim_type"],
                                "raw": claim["raw"],
                                "value": claim["value"],
                                "unit": claim["unit"],
                                "source_surface_status": status,
                                "matching_source_sentences": matching_sentences_for_value(
                                    claim["value"], article["content"]
                                ),
                                "human_verdict": "",
                                "reviewer_id": "",
                                "reviewer_note": "",
                            }
                        )

    if args.blind:
        rng = random.Random(args.seed)
        indices = list(range(len(rows)))
        rng.shuffle(indices)
        blind_rows = []
        key_rows = []
        for idx, row_idx in enumerate(indices, start=1):
            eval_id = f"BLIND-{args.split.upper()}-{idx:03d}"
            r = dict(rows[row_idx])
            key_rows.append(
                {
                    "eval_id": eval_id,
                    "item_id": r["item_id"],
                    "split": r["split"],
                    "experiment": r["experiment"],
                    "run_label": r["run_label"],
                    "model_id": r["model_id"],
                }
            )
            r["eval_id"] = eval_id
            blind_rows.append(r)
        rows = blind_rows
        write_csv_atomic(reports_dir / f".blind_key_{args.split}.csv", BLIND_KEY_COLUMNS, key_rows)

    write_csv_atomic(default_sheet, HUMAN_EVAL_COLUMNS, rows)
    error_table_path = reports_dir / "numeric_error_table.csv"
    write_csv_atomic(error_table_path, NUMERIC_ERROR_COLUMNS, error_rows)
    print(f"Wrote {len(rows)} rows to {default_sheet}")
    print(f"Wrote {len(error_rows)} rows to {error_table_path}")


if __name__ == "__main__":
    main()
