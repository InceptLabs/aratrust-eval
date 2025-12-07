#!/usr/bin/env python3
"""Compare two evaluation runs from Langfuse with detailed analysis."""

import sys
sys.path.insert(0, "/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval")

from langfuse import Langfuse
from src.config import Config
from collections import defaultdict
import json

config = Config()
langfuse = Langfuse(
    host=config.LANGFUSE_HOST,
    public_key=config.LANGFUSE_PUBLIC_KEY,
    secret_key=config.LANGFUSE_SECRET_KEY,
)

def fetch_all_traces(tags=None, limit_per_page=100):
    """Fetch all traces with pagination."""
    all_traces = []
    page = 1
    while True:
        if tags:
            traces = langfuse.fetch_traces(tags=tags, limit=limit_per_page, page=page)
        else:
            traces = langfuse.fetch_traces(limit=limit_per_page, page=page)
        if not traces.data:
            break
        all_traces.extend(traces.data)
        print(f"  Fetched page {page}: {len(traces.data)} traces")
        page += 1
    return all_traces

def get_unique_sessions():
    """Get all unique session IDs (run IDs) from traces."""
    print("Fetching all traces to identify unique runs...")
    all_traces = fetch_all_traces()

    sessions = defaultdict(list)
    for trace in all_traces:
        if trace.session_id:
            sessions[trace.session_id].append(trace)

    print(f"\nFound {len(sessions)} unique runs:")
    for session_id, traces in sorted(sessions.items()):
        print(f"  - {session_id}: {len(traces)} traces")

    return sessions

def analyze_run(traces, run_name="Run"):
    """Analyze a single run's traces."""
    print(f"\n{'='*60}")
    print(f"ANALYSIS: {run_name}")
    print(f"{'='*60}")

    total = len(traces)
    correct = sum(1 for t in traces if t.metadata and t.metadata.get("is_correct") is True)
    incorrect = sum(1 for t in traces if t.metadata and t.metadata.get("is_correct") is False)

    print(f"\nOverall Statistics:")
    print(f"  Total samples: {total}")
    print(f"  Correct: {correct}")
    print(f"  Incorrect: {incorrect}")
    print(f"  Accuracy: {correct/total*100:.2f}%" if total > 0 else "  Accuracy: N/A")

    # Per-category analysis
    categories = defaultdict(lambda: {"total": 0, "correct": 0, "incorrect": 0, "samples": []})

    for trace in traces:
        if trace.metadata:
            cat = trace.metadata.get("category", "Unknown")
            is_correct = trace.metadata.get("is_correct")
            categories[cat]["total"] += 1
            if is_correct is True:
                categories[cat]["correct"] += 1
            elif is_correct is False:
                categories[cat]["incorrect"] += 1
                categories[cat]["samples"].append({
                    "sample_idx": trace.metadata.get("sample_idx"),
                    "subcategory": trace.metadata.get("subcategory"),
                    "correct_answer": trace.metadata.get("correct_answer"),
                    "predicted": trace.output.get("predicted") if trace.output else None,
                    "trace_id": trace.id,
                })

    print(f"\nPer-Category Breakdown:")
    print(f"{'Category':<20} {'Total':>8} {'Correct':>8} {'Incorrect':>8} {'Accuracy':>10}")
    print("-" * 60)

    for cat in sorted(categories.keys(), key=lambda x: x or ""):
        data = categories[cat]
        acc = data["correct"] / data["total"] * 100 if data["total"] > 0 else 0
        cat_display = cat if cat else "(Unknown)"
        print(f"{cat_display:<20} {data['total']:>8} {data['correct']:>8} {data['incorrect']:>8} {acc:>9.2f}%")

    return {
        "total": total,
        "correct": correct,
        "incorrect": incorrect,
        "accuracy": correct/total*100 if total > 0 else 0,
        "categories": dict(categories)
    }

def compare_runs(run1_data, run2_data, run1_name, run2_name):
    """Compare two runs and show detailed differences."""
    print(f"\n{'='*80}")
    print("COMPARISON ANALYSIS")
    print(f"{'='*80}")

    # Overall comparison
    print(f"\n{'Metric':<25} {run1_name:>20} {run2_name:>20} {'Change':>15}")
    print("-" * 80)

    acc_diff = run2_data["accuracy"] - run1_data["accuracy"]
    print(f"{'Overall Accuracy':<25} {run1_data['accuracy']:>19.2f}% {run2_data['accuracy']:>19.2f}% {acc_diff:>+14.2f}%")
    print(f"{'Total Correct':<25} {run1_data['correct']:>20} {run2_data['correct']:>20} {run2_data['correct']-run1_data['correct']:>+15}")
    print(f"{'Total Incorrect':<25} {run1_data['incorrect']:>20} {run2_data['incorrect']:>20} {run2_data['incorrect']-run1_data['incorrect']:>+15}")

    # Per-category comparison
    print(f"\n{'='*80}")
    print("PER-CATEGORY COMPARISON")
    print(f"{'='*80}")

    all_cats = set(run1_data["categories"].keys()) | set(run2_data["categories"].keys())

    print(f"\n{'Category':<20} {run1_name+' Acc':>15} {run2_name+' Acc':>15} {'Change':>12} {'Status':>10}")
    print("-" * 80)

    improvements = []
    regressions = []

    for cat in sorted(all_cats, key=lambda x: x or ""):
        cat1 = run1_data["categories"].get(cat, {"total": 0, "correct": 0})
        cat2 = run2_data["categories"].get(cat, {"total": 0, "correct": 0})

        acc1 = cat1["correct"] / cat1["total"] * 100 if cat1["total"] > 0 else 0
        acc2 = cat2["correct"] / cat2["total"] * 100 if cat2["total"] > 0 else 0
        diff = acc2 - acc1

        if diff > 0:
            status = "IMPROVED"
            improvements.append((cat, diff))
        elif diff < 0:
            status = "REGRESSED"
            regressions.append((cat, diff))
        else:
            status = "SAME"

        cat_display = cat if cat else "(Unknown)"
        print(f"{cat_display:<20} {acc1:>14.2f}% {acc2:>14.2f}% {diff:>+11.2f}% {status:>10}")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    if improvements:
        print(f"\nCategories that IMPROVED ({len(improvements)}):")
        for cat, diff in sorted(improvements, key=lambda x: -x[1]):
            print(f"  + {cat}: +{diff:.2f}%")

    if regressions:
        print(f"\nCategories that REGRESSED ({len(regressions)}):")
        for cat, diff in sorted(regressions, key=lambda x: x[1]):
            print(f"  - {cat}: {diff:.2f}%")

    # Detailed incorrect sample comparison
    print(f"\n{'='*80}")
    print("INCORRECT SAMPLES ANALYSIS")
    print(f"{'='*80}")

    for cat in sorted(all_cats, key=lambda x: x or ""):
        cat1 = run1_data["categories"].get(cat, {"samples": []})
        cat2 = run2_data["categories"].get(cat, {"samples": []})

        samples1_idx = set(s["sample_idx"] for s in cat1.get("samples", []))
        samples2_idx = set(s["sample_idx"] for s in cat2.get("samples", []))

        fixed = samples1_idx - samples2_idx  # Was wrong in run1, correct in run2
        broken = samples2_idx - samples1_idx  # Was correct in run1, wrong in run2
        still_wrong = samples1_idx & samples2_idx  # Wrong in both

        if fixed or broken:
            print(f"\n{cat}:")
            if fixed:
                print(f"  Fixed samples (now correct): {len(fixed)}")
                for idx in sorted(fixed):
                    sample = next((s for s in cat1["samples"] if s["sample_idx"] == idx), None)
                    if sample:
                        print(f"    - Sample {idx}: was predicting '{sample['predicted']}', correct is '{sample['correct_answer']}'")
            if broken:
                print(f"  Broken samples (now incorrect): {len(broken)}")
                for idx in sorted(broken):
                    sample = next((s for s in cat2["samples"] if s["sample_idx"] == idx), None)
                    if sample:
                        print(f"    - Sample {idx}: now predicting '{sample['predicted']}', correct is '{sample['correct_answer']}'")
            if still_wrong:
                print(f"  Still incorrect in both runs: {len(still_wrong)}")

def main():
    print("="*80)
    print("LANGFUSE EVALUATION RUNS COMPARISON")
    print("="*80)

    # Get all sessions
    sessions = get_unique_sessions()

    if len(sessions) < 2:
        print("\nNeed at least 2 runs to compare. Found:", len(sessions))
        return

    # Filter for actual evaluation runs (with 522 traces)
    eval_sessions = {k: v for k, v in sessions.items() if len(v) >= 500}

    if len(eval_sessions) < 2:
        print(f"\nNeed at least 2 full evaluation runs. Found: {len(eval_sessions)}")
        return

    # Get the two evaluation runs
    sorted_sessions = sorted(eval_sessions.items(), key=lambda x: x[0])

    run1_id, run1_traces = sorted_sessions[0]
    run2_id, run2_traces = sorted_sessions[1]

    print(f"\nComparing:")
    print(f"  Run 1: {run1_id} ({len(run1_traces)} traces)")
    print(f"  Run 2: {run2_id} ({len(run2_traces)} traces)")

    # Analyze each run
    run1_data = analyze_run(run1_traces, run1_id)
    run2_data = analyze_run(run2_traces, run2_id)

    # Compare runs
    compare_runs(run1_data, run2_data, run1_id, run2_id)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
