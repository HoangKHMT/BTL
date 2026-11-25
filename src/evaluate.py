#!/usr/bin/env python3
"""Generate/evaluate per-item summaries without exposing test data by default."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import unicodedata
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from rouge_score.rouge_scorer import RougeScorer

from check_gold import analyze, split_sentences, to_float, unit_related, unorm


PROTOCOL_TAG = "protocol-frozen"
PROTOCOL_COMMIT = "072666a471383d8596c03c28a70ec2c2ad6ee363"
EXPERIMENT_COLUMNS = [
    "run_id",
    "run_timestamp",
    "experiment",
    "split",
    "method",
    "model_id",
    "run_label",
    "prompt_version",
    "temperature",
    "api_endpoint",
    "run_commit",
    "source_fingerprint",
    "worktree_status",
    "protocol_tag",
    "protocol_commit",
    "config_tag",
    "config_tag_commit",
    "postcheck_policy",
    "sample_count",
    "output_file",
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
    "status",
]
PREDICTION_COLUMNS = [
    "item_id",
    "split",
    "experiment",
    "source_revision",
    "run_commit",
    "source_fingerprint",
    "worktree_status",
    "model_id",
    "run_label",
    "prompt_version",
    "temperature",
    "api_endpoint",
    "postcheck_applied",
    "summary_before_postcheck",
    "summary_after_postcheck",
    "reference_summary",
    "rouge1_f1_before",
    "rouge2_f1_before",
    "rougeL_f1_before",
    "rouge1_f1_after",
    "rouge2_f1_after",
    "rougeL_f1_after",
    "numeric_claims_before",
    "exact_value_unit_matches_before",
    "source_value_not_found_before",
    "exact_value_unit_match_rate_before",
    "gold_fact_count",
    "gold_facts_matched_before",
    "gold_fact_surface_recall_before",
    "numeric_claims_after",
    "exact_value_unit_matches_after",
    "source_value_not_found_after",
    "exact_value_unit_match_rate_after",
    "gold_facts_matched_after",
    "gold_fact_surface_recall_after",
    "output_numeric_claims",
    "supported_claims",
    "unsupported_claims",
    "contradicted_claims",
    "numeric_precision",
    "numeric_hallucination_rate",
    "gold_numeric_recall",
    "factuality_score",
    "human_review_status",
    "reviewer_note",
]
CLAIM_COLUMNS = [
    "item_id",
    "split",
    "experiment",
    "stage",
    "claim_type",
    "raw",
    "value",
    "unit",
    "source_surface_status",
    "human_review_status",
]
POSTCHECK_POLICIES = {
    "regenerate_once_then_drop",
    "drop_sentence",
    "flag_only",
}


class SyllableTokenizer:
    """Whitespace-delimited Vietnamese syllables after Unicode normalization."""

    def tokenize(self, text: str) -> list[str]:
        normalized = unicodedata.normalize("NFC", text).casefold()
        return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def lead3(text: str) -> str:
    return " ".join(split_sentences(text)[:3])


def load_articles(path: Path, split: str) -> dict[str, dict[str, Any]]:
    articles: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            article = json.loads(line)
            if article.get("split") != split:
                continue
            item_id = str(article["item_id"])
            if item_id in articles:
                raise ValueError(f"{path}:{line_number}: duplicate item_id {item_id}")
            articles[item_id] = article
    return articles


def load_references(path: Path, split: str) -> dict[str, dict[str, str]]:
    references: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("split") != split:
                continue
            item_id = row.get("item_id", "").strip()
            summary = row.get("reference_summary", "").strip()
            if not item_id or not summary:
                raise ValueError(f"Missing item_id or reference_summary for split={split}")
            if item_id in references:
                raise ValueError(f"Duplicate gold reference for {item_id}")
            references[item_id] = row
    return references


def load_gold_facts(path: Path) -> dict[str, set[tuple[float, str]]]:
    facts: dict[str, set[tuple[float, str]]] = defaultdict(set)
    if not path.exists():
        return facts
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            item_id = row.get("item_id", "").strip()
            value = row.get("value", "").strip()
            unit = unorm(row.get("unit", ""))
            if not item_id or not value:
                continue
            try:
                facts[item_id].add((to_float(value), unit))
            except ValueError as error:
                raise ValueError(f"Invalid gold numeric value for {item_id}: {value}") from error
    return facts


def load_source_revision(path: Path) -> str:
    with path.open(encoding="utf-8-sig", newline="") as file:
        revisions = {
            row.get("source_version", "").strip()
            for row in csv.DictReader(file)
            if row.get("source_version", "").strip()
        }
    if len(revisions) != 1:
        raise ValueError(
            f"Expected one source_version in {path}, found {sorted(revisions)}"
        )
    return revisions.pop()


def load_external_predictions(
    path: Path,
    experiment: str,
) -> dict[str, tuple[str, str]]:
    required = (
        {"item_id", "summary"}
        if experiment == "E1"
        else {"item_id", "summary_before", "summary_after"}
    )
    predictions: dict[str, tuple[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"{path} must contain columns: {', '.join(sorted(required))}"
            )
        for row in reader:
            item_id = row.get("item_id", "").strip()
            if not item_id:
                raise ValueError(f"{path}: prediction row has an empty item_id")
            if item_id in predictions:
                raise ValueError(f"{path}: duplicate prediction for {item_id}")
            if experiment == "E1":
                summary = row.get("summary", "").strip()
                predictions[item_id] = (summary, summary)
            else:
                before = row.get("summary_before", "").strip()
                after = row.get("summary_after", "").strip()
                predictions[item_id] = (before, after)
    return predictions


def numeric_claims(text: str) -> list[dict[str, str]]:
    parsed = analyze(text)
    claims = [
        {"claim_type": "fact", "value": value, "unit": unit, "raw": f"{value} {unit}".strip()}
        for value, unit in parsed["facts"]
    ]
    claims.extend(
        {
            "claim_type": "dot_decimal",
            "value": value,
            "unit": unit,
            "raw": f"{value}{unit}",
        }
        for value, unit in parsed["dotdec"]
    )
    claims.extend(
        {"claim_type": "bare", "value": value, "unit": "", "raw": value}
        for value in parsed["bare"]
    )
    return claims


def source_surface_status(
    claim: dict[str, str],
    source_analysis: dict[str, Any],
) -> str:
    try:
        value = to_float(claim["value"])
        source_values = {to_float(token) for token in source_analysis["tokens"]}
        source_values.update(
            to_float(source_value)
            for source_value, _ in source_analysis["facts"]
        )
        source_values.update(
            to_float(source_value)
            for source_value, _ in source_analysis["dotdec"]
        )
        if value not in source_values:
            return "not_found"
        if not claim["unit"]:
            return "value_only"

        source_units = {
            unit
            for source_value, unit in source_analysis["facts"]
            if to_float(source_value) == value
        }
        source_units.update(
            unit
            for source_value, unit in source_analysis["dotdec"]
            if unit and to_float(source_value) == value
        )
        if claim["unit"] in source_units or any(
            unit_related(claim["unit"], source_unit) for source_unit in source_units
        ):
            return "value_unit_match"
        if source_units:
            return "value_unit_differs"
        return "value_only"
    except ValueError:
        return "not_found"


def gold_fact_recall(
    claims: list[dict[str, str]],
    gold_facts: set[tuple[float, str]],
) -> tuple[int, str]:
    if not gold_facts:
        return 0, ""
    matched: set[tuple[float, str]] = set()
    for gold_value, gold_unit in gold_facts:
        for claim in claims:
            try:
                claim_value = to_float(claim["value"])
            except ValueError:
                continue
            claim_unit = unorm(claim["unit"])
            if claim_value == gold_value and (
                claim_unit == gold_unit
                or bool(claim_unit and gold_unit and unit_related(claim_unit, gold_unit))
                or not claim_unit and not gold_unit
            ):
                matched.add((gold_value, gold_unit))
                break
    return len(matched), f"{len(matched) / len(gold_facts):.6f}"


def stage_metrics(
    prediction: str,
    reference: str,
    source: str,
    gold_facts: set[tuple[float, str]],
    scorer: RougeScorer,
) -> dict[str, Any]:
    scores = scorer.score(reference, prediction)
    claims = numeric_claims(prediction)
    source_analysis = analyze(source)
    statuses = [source_surface_status(claim, source_analysis) for claim in claims]
    surface_supported = sum(status == "value_unit_match" for status in statuses)
    unmatched = sum(status == "not_found" for status in statuses)
    matched_gold, recall = gold_fact_recall(claims, gold_facts)
    surface_rate = (
        f"{surface_supported / len(claims):.6f}" if claims else ""
    )
    return {
        "rouge1_f1": scores["rouge1"].fmeasure,
        "rouge2_f1": scores["rouge2"].fmeasure,
        "rougeL_f1": scores["rougeL"].fmeasure,
        "claims": claims,
        "surface_supported": surface_supported,
        "surface_unmatched": unmatched,
        "surface_match_rate": surface_rate,
        "gold_facts_matched": matched_gold,
        "gold_fact_surface_recall": recall,
        "statuses": statuses,
    }


def source_fingerprint(root: Path) -> str:
    ignored_directories = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "reports"}
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or ignored_directories.intersection(relative.parts[:-1]):
            continue
        digest.update(relative.as_posix().encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest()


def resolve_run_provenance(root: Path, explicit: str | None) -> tuple[str, str, str]:
    fingerprint = source_fingerprint(root)
    if explicit:
        commit = explicit.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{7,40}", commit):
            raise ValueError("--run-commit must be a Git commit hash")
        return commit, fingerprint, "explicit_revision"
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "", fingerprint, "uncommitted"
    commit = result.stdout.strip().lower()
    if result.returncode or not re.fullmatch(r"[0-9a-f]{7,40}", commit):
        return "", fingerprint, "uncommitted"
    try:
        status = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return commit, fingerprint, "unknown"
    if status.returncode:
        return commit, fingerprint, "unknown"
    return commit, fingerprint, "dirty" if status.stdout.strip() else "clean"


def verify_tag_commit(repo_root: Path | None, tag: str, expected: str) -> None:
    if repo_root is None:
        return
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", f"{tag}^{{}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError(f"Git tag {tag!r} was not found in {repo_root}")
    if result.stdout.strip() != expected:
        raise ValueError(
            f"Git tag {tag!r} resolves to {result.stdout.strip()}, expected {expected}"
        )


def write_csv_atomic(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def mean_metric(rows: list[dict[str, Any]], field: str) -> str:
    values = [float(row[field]) for row in rows if row.get(field) not in ("", None)]
    return f"{mean(values):.6f}" if values else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--split", choices=("dev", "test"), default="dev")
    parser.add_argument("--experiment", choices=("E0", "E1", "E2"), default="E0")
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--model-id")
    parser.add_argument("--run-label")
    parser.add_argument("--prompt-version")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--api-endpoint")
    parser.add_argument("--run-commit")
    parser.add_argument("--config-tag", default="configs-frozen")
    parser.add_argument("--config-tag-commit")
    parser.add_argument("--confirm-test-once", action="store_true")
    parser.add_argument(
        "--postcheck-policy",
        choices=sorted(POSTCHECK_POLICIES),
        default="regenerate_once_then_drop",
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    root = args.root.resolve()
    repo_root = args.repo_root.resolve() if args.repo_root else None
    run_commit, source_hash, worktree_status = resolve_run_provenance(
        repo_root or root, args.run_commit
    )
    verify_tag_commit(repo_root, PROTOCOL_TAG, PROTOCOL_COMMIT)
    config_tag_commit = args.config_tag_commit or ""
    if args.split == "test":
        if not args.confirm_test_once or not config_tag_commit:
            parser.error(
                "test scoring requires --confirm-test-once and --config-tag-commit after configurations are frozen"
            )
        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", config_tag_commit):
            parser.error("--config-tag-commit must be a Git commit hash")
        if repo_root is not None:
            verify_tag_commit(repo_root, args.config_tag, config_tag_commit.lower())
    elif config_tag_commit:
        parser.error("--config-tag-commit is only valid for a test run")

    if args.experiment == "E0":
        if any((args.predictions, args.model_id, args.prompt_version, args.temperature, args.api_endpoint)):
            parser.error("E0 Lead-3 is generated locally; do not pass model or prediction metadata")
        method = "Lead-3"
        model_id = "Lead-3"
        prompt_version = ""
        temperature = ""
        api_endpoint = ""
        postcheck_policy = "not_applicable"
    else:
        if not all(
            (
                args.predictions,
                args.model_id,
                args.prompt_version,
                args.temperature is not None,
                args.api_endpoint,
            )
        ):
            parser.error(
                "E1/E2 require --predictions, --model-id, --prompt-version, --temperature, and --api-endpoint"
            )
        method = "prompted_model"
        model_id = args.model_id
        prompt_version = args.prompt_version
        temperature = args.temperature
        api_endpoint = args.api_endpoint
        postcheck_policy = (
            args.postcheck_policy if args.experiment == "E2" else "not_applicable"
        )

    run_label = args.run_label or ""
    if run_label and not re.fullmatch(r"[A-Za-z0-9._-]+", run_label):
        parser.error("--run-label may contain only letters, numbers, '.', '_' and '-'")
    output_dir = args.output_dir.resolve() if args.output_dir else root / "reports"
    suffix = f"_{run_label}" if run_label else ""
    predictions_path = output_dir / f"{args.split}_predictions_{args.experiment}{suffix}.csv"
    claims_path = output_dir / f"{args.split}_numeric_claims_{args.experiment}{suffix}.csv"
    experiments_path = output_dir / "experiments.csv"
    if args.split == "test":
        if predictions_path.exists():
            parser.error(f"Refusing to overwrite locked test output: {predictions_path}")
        if experiments_path.exists():
            with experiments_path.open(encoding="utf-8-sig", newline="") as file:
                prior_runs = list(csv.DictReader(file))
            if any(
                row.get("split") == "test"
                and row.get("experiment") == args.experiment
                and row.get("status") == "completed"
                for row in prior_runs
            ):
                parser.error(
                    f"{args.experiment} already has a completed test run in {experiments_path}"
                )

    article_path = root / "data/processed/selected_articles.jsonl"
    gold_path = root / "data/annotations/gold_summaries.csv"
    numeric_path = root / "data/annotations/gold_numeric_facts.csv"
    manifest_path = root / "data/data_manifest.csv"
    for required_path in (article_path, gold_path, manifest_path):
        if not required_path.exists():
            parser.error(f"Required file not found: {required_path}")

    source_revision = load_source_revision(manifest_path)
    articles = load_articles(article_path, args.split)
    references = load_references(gold_path, args.split)
    if set(articles) != set(references):
        missing_refs = sorted(set(articles) - set(references))
        missing_articles = sorted(set(references) - set(articles))
        parser.error(
            f"Article/reference IDs differ; missing refs={missing_refs}, missing articles={missing_articles}"
        )
    if not articles:
        parser.error(f"No items found for split {args.split}")

    if args.experiment == "E0":
        predictions = {
            item_id: (lead3(article["content"]), lead3(article["content"]))
            for item_id, article in articles.items()
        }
    else:
        prediction_path = args.predictions
        if not prediction_path.is_absolute():
            prediction_path = root / prediction_path
        predictions = load_external_predictions(prediction_path, args.experiment)
        if set(predictions) != set(articles):
            missing = sorted(set(articles) - set(predictions))
            extra = sorted(set(predictions) - set(articles))
            parser.error(f"Prediction IDs differ; missing={missing}, extra={extra}")
        if any(
            not before or (not after and args.experiment != "E2")
            for before, after in predictions.values()
        ):
            parser.error("Prediction file contains an empty required summary")

    gold_facts = load_gold_facts(numeric_path)
    scorer = RougeScorer(
        ["rouge1", "rouge2", "rougeL"],
        use_stemmer=False,
        tokenizer=SyllableTokenizer(),
    )
    prediction_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, str]] = []
    for item_id in sorted(articles):
        article = articles[item_id]
        reference = references[item_id]["reference_summary"]
        before, after = predictions[item_id]
        gold_item_facts = gold_facts.get(item_id, set())
        before_metrics = stage_metrics(
            before, reference, article["content"], gold_item_facts, scorer
        )
        after_metrics = stage_metrics(
            after, reference, article["content"], gold_item_facts, scorer
        )
        prediction_rows.append(
            {
                "item_id": item_id,
                "split": args.split,
                "experiment": args.experiment,
                "source_revision": source_revision,
                "run_commit": run_commit,
                "source_fingerprint": source_hash,
                "worktree_status": worktree_status,
                "model_id": model_id,
                "run_label": run_label,
                "prompt_version": prompt_version,
                "temperature": temperature,
                "api_endpoint": api_endpoint,
                "postcheck_applied": args.experiment == "E2",
                "summary_before_postcheck": before,
                "summary_after_postcheck": after,
                "reference_summary": reference,
                **{
                    f"{metric}_before": before_metrics[metric]
                    for metric in ("rouge1_f1", "rouge2_f1", "rougeL_f1")
                },
                **{
                    f"{metric}_after": after_metrics[metric]
                    for metric in ("rouge1_f1", "rouge2_f1", "rougeL_f1")
                },
                "numeric_claims_before": len(before_metrics["claims"]),
                "exact_value_unit_matches_before": before_metrics["surface_supported"],
                "source_value_not_found_before": before_metrics["surface_unmatched"],
                "exact_value_unit_match_rate_before": before_metrics["surface_match_rate"],
                "gold_fact_count": len(gold_item_facts),
                "gold_facts_matched_before": before_metrics["gold_facts_matched"],
                "gold_fact_surface_recall_before": before_metrics["gold_fact_surface_recall"],
                "numeric_claims_after": len(after_metrics["claims"]),
                "exact_value_unit_matches_after": after_metrics["surface_supported"],
                "source_value_not_found_after": after_metrics["surface_unmatched"],
                "exact_value_unit_match_rate_after": after_metrics["surface_match_rate"],
                "gold_facts_matched_after": after_metrics["gold_facts_matched"],
                "gold_fact_surface_recall_after": after_metrics["gold_fact_surface_recall"],
                "output_numeric_claims": len(after_metrics["claims"]),
                "supported_claims": "",
                "unsupported_claims": "",
                "contradicted_claims": "",
                "numeric_precision": "",
                "numeric_hallucination_rate": "",
                "gold_numeric_recall": "",
                "factuality_score": "",
                "human_review_status": "pending",
                "reviewer_note": "",
            }
        )
        audit_stages = (
            (("before_postcheck", before_metrics), ("after_postcheck", after_metrics))
            if args.experiment == "E2"
            else (("prediction", after_metrics),)
        )
        for stage, metrics in audit_stages:
            for claim, status in zip(metrics["claims"], metrics["statuses"], strict=True):
                claim_rows.append(
                    {
                        "item_id": item_id,
                        "split": args.split,
                        "experiment": args.experiment,
                        "stage": stage,
                        **claim,
                        "source_surface_status": status,
                        "human_review_status": "pending",
                    }
                )

    write_csv_atomic(predictions_path, PREDICTION_COLUMNS, prediction_rows)
    write_csv_atomic(claims_path, CLAIM_COLUMNS, claim_rows)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    run_record = {
        "run_id": f"{timestamp.replace(':', '-')}-{uuid.uuid4().hex[:8]}",
        "run_timestamp": timestamp,
        "experiment": args.experiment,
        "split": args.split,
        "method": method,
        "model_id": model_id,
        "run_label": run_label,
        "prompt_version": prompt_version,
        "temperature": temperature,
        "api_endpoint": api_endpoint,
        "run_commit": run_commit,
        "source_fingerprint": source_hash,
        "worktree_status": worktree_status,
        "protocol_tag": PROTOCOL_TAG,
        "protocol_commit": PROTOCOL_COMMIT,
        "config_tag": args.config_tag if args.split == "test" else "",
        "config_tag_commit": config_tag_commit,
        "postcheck_policy": postcheck_policy,
        "sample_count": len(prediction_rows),
        "output_file": str(predictions_path.relative_to(root))
        if predictions_path.is_relative_to(root)
        else str(predictions_path),
        "numeric_claims_before": sum(int(row["numeric_claims_before"]) for row in prediction_rows),
        "exact_value_unit_matches_before": sum(
            int(row["exact_value_unit_matches_before"]) for row in prediction_rows
        ),
        "exact_value_unit_match_rate_before": (
            f"{sum(int(row['exact_value_unit_matches_before']) for row in prediction_rows) / sum(int(row['numeric_claims_before']) for row in prediction_rows):.6f}"
            if sum(int(row["numeric_claims_before"]) for row in prediction_rows)
            else ""
        ),
        "numeric_claims_after": sum(int(row["numeric_claims_after"]) for row in prediction_rows),
        "exact_value_unit_matches_after": sum(
            int(row["exact_value_unit_matches_after"]) for row in prediction_rows
        ),
        "exact_value_unit_match_rate_after": (
            f"{sum(int(row['exact_value_unit_matches_after']) for row in prediction_rows) / sum(int(row['numeric_claims_after']) for row in prediction_rows):.6f}"
            if sum(int(row["numeric_claims_after"]) for row in prediction_rows)
            else ""
        ),
        "gold_fact_surface_recall_before_macro": mean_metric(
            prediction_rows, "gold_fact_surface_recall_before"
        ),
        "gold_fact_surface_recall_after_macro": mean_metric(
            prediction_rows, "gold_fact_surface_recall_after"
        ),
        "status": "completed",
    }
    for metric in ("rouge1_f1", "rouge2_f1", "rougeL_f1"):
        run_record[f"{metric}_before_macro"] = mean_metric(prediction_rows, f"{metric}_before")
        run_record[f"{metric}_after_macro"] = mean_metric(prediction_rows, f"{metric}_after")

    previous_runs: list[dict[str, str]] = []
    if experiments_path.exists():
        with experiments_path.open(encoding="utf-8-sig", newline="") as file:
            previous_runs = list(csv.DictReader(file))
    write_csv_atomic(
        experiments_path,
        EXPERIMENT_COLUMNS,
        [*previous_runs, run_record],
    )

    print(
        f"{args.experiment} {args.split}: n={len(prediction_rows)}; "
        f"ROUGE-L before={run_record['rougeL_f1_before_macro']}; "
        f"exact value+unit match={run_record['exact_value_unit_match_rate_before'] or 'N/A'}"
    )
    print(f"Wrote {predictions_path}")
    print(f"Wrote {claims_path}")
    print(f"Updated {experiments_path}")


if __name__ == "__main__":
    main()
