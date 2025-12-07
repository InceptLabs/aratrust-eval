#!/usr/bin/env python3
"""Analyze persistent errors - samples wrong in both runs."""

import sys
sys.path.insert(0, "/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval")

from langfuse import Langfuse
from src.config import Config
from collections import defaultdict, Counter
import pandas as pd

config = Config()
langfuse = Langfuse(
    host=config.LANGFUSE_HOST,
    public_key=config.LANGFUSE_PUBLIC_KEY,
    secret_key=config.LANGFUSE_SECRET_KEY,
)

def fetch_all_traces(limit_per_page=100):
    """Fetch all traces with pagination."""
    all_traces = []
    page = 1
    while True:
        traces = langfuse.fetch_traces(limit=limit_per_page, page=page)
        if not traces.data:
            break
        all_traces.extend(traces.data)
        page += 1
    return all_traces

def main():
    print("="*80)
    print("PERSISTENT ERRORS ANALYSIS")
    print("Samples incorrect in BOTH Run 1 and Run 2")
    print("="*80)

    print("\nFetching traces from Langfuse...")
    all_traces = fetch_all_traces()

    # Group by session
    sessions = defaultdict(list)
    for trace in all_traces:
        if trace.session_id:
            sessions[trace.session_id].append(trace)

    # Get evaluation runs
    eval_sessions = {k: v for k, v in sessions.items() if len(v) >= 500}
    sorted_sessions = sorted(eval_sessions.items(), key=lambda x: x[0])

    run1_id, run1_traces = sorted_sessions[0]
    run2_id, run2_traces = sorted_sessions[1]

    print(f"\nRun 1: {run1_id}")
    print(f"Run 2: {run2_id}")

    # Find incorrect samples in each run
    run1_incorrect = set()
    run2_incorrect = set()

    run1_data = {}
    run2_data = {}

    for trace in run1_traces:
        if trace.metadata and trace.metadata.get("is_correct") is False:
            idx = trace.metadata.get("sample_idx")
            run1_incorrect.add(idx)
            run1_data[idx] = {
                "category": trace.metadata.get("category"),
                "subcategory": trace.metadata.get("subcategory"),
                "correct_answer": trace.metadata.get("correct_answer"),
                "predicted": trace.output.get("predicted") if trace.output else None,
            }

    for trace in run2_traces:
        if trace.metadata and trace.metadata.get("is_correct") is False:
            idx = trace.metadata.get("sample_idx")
            run2_incorrect.add(idx)
            run2_data[idx] = {
                "category": trace.metadata.get("category"),
                "subcategory": trace.metadata.get("subcategory"),
                "correct_answer": trace.metadata.get("correct_answer"),
                "predicted": trace.output.get("predicted") if trace.output else None,
            }

    # Find persistent errors (wrong in both)
    persistent = run1_incorrect & run2_incorrect

    print(f"\nRun 1 incorrect: {len(run1_incorrect)}")
    print(f"Run 2 incorrect: {len(run2_incorrect)}")
    print(f"Persistent (wrong in both): {len(persistent)}")

    # Analyze by category
    print(f"\n{'='*80}")
    print("PERSISTENT ERRORS BY CATEGORY")
    print("="*80)

    cat_persistent = defaultdict(list)
    for idx in persistent:
        data = run2_data.get(idx, run1_data.get(idx))
        if data:
            cat_persistent[data["category"]].append({
                "sample_idx": idx,
                **data
            })

    print(f"\n{'Category':<20} {'Persistent':>10} {'% of Total':>12}")
    print("-" * 45)

    # Category totals from full dataset
    df = pd.read_csv("/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval/results/eval_v1.0_zero_shot.csv")
    cat_totals = df.groupby('category').size().to_dict()

    for cat in sorted(cat_persistent.keys(), key=lambda x: -len(cat_persistent[x])):
        count = len(cat_persistent[cat])
        total = cat_totals.get(cat, 0)
        pct = count / total * 100 if total > 0 else 0
        print(f"{cat:<20} {count:>10} {pct:>11.1f}%")

    # Analyze by subcategory
    print(f"\n{'='*80}")
    print("PERSISTENT ERRORS BY SUBCATEGORY")
    print("="*80)

    subcat_persistent = defaultdict(list)
    for idx in persistent:
        data = run2_data.get(idx, run1_data.get(idx))
        if data:
            key = f"{data['category']} / {data['subcategory']}"
            subcat_persistent[key].append(idx)

    print(f"\n{'Category / Subcategory':<45} {'Count':>8}")
    print("-" * 55)

    for subcat in sorted(subcat_persistent.keys(), key=lambda x: -len(subcat_persistent[x])):
        count = len(subcat_persistent[subcat])
        print(f"{subcat:<45} {count:>8}")

    # Check if predictions are consistent between runs
    print(f"\n{'='*80}")
    print("PREDICTION CONSISTENCY ANALYSIS")
    print("="*80)

    consistent_wrong = 0
    different_wrong = 0

    for idx in persistent:
        r1 = run1_data.get(idx)
        r2 = run2_data.get(idx)
        if r1 and r2:
            if r1["predicted"] == r2["predicted"]:
                consistent_wrong += 1
            else:
                different_wrong += 1

    print(f"\nSame wrong answer in both runs: {consistent_wrong}")
    print(f"Different wrong answers in both runs: {different_wrong}")

    # Show samples with different wrong answers (interesting cases)
    print(f"\n{'='*80}")
    print("SAMPLES WITH DIFFERENT WRONG PREDICTIONS")
    print("(Model gave different wrong answers in each run)")
    print("="*80)

    diff_samples = []
    for idx in persistent:
        r1 = run1_data.get(idx)
        r2 = run2_data.get(idx)
        if r1 and r2 and r1["predicted"] != r2["predicted"]:
            diff_samples.append({
                "idx": idx,
                "category": r2["category"],
                "subcategory": r2["subcategory"],
                "correct": r2["correct_answer"],
                "run1_pred": r1["predicted"],
                "run2_pred": r2["predicted"],
            })

    for s in sorted(diff_samples, key=lambda x: x["idx"]):
        print(f"\nSample {s['idx']} ({s['category']} / {s['subcategory']}):")
        print(f"  Correct: {s['correct']}")
        print(f"  Run 1 predicted: {s['run1_pred']}")
        print(f"  Run 2 predicted: {s['run2_pred']}")

    # Full list of persistent errors
    print(f"\n{'='*80}")
    print("ALL PERSISTENT ERRORS")
    print("="*80)

    for cat in sorted(cat_persistent.keys()):
        print(f"\n--- {cat} ({len(cat_persistent[cat])} samples) ---")
        for sample in sorted(cat_persistent[cat], key=lambda x: x["sample_idx"]):
            print(f"  Sample {sample['sample_idx']:>3}: {sample['subcategory']:<25} "
                  f"predicted '{sample['predicted']}' (correct: '{sample['correct_answer']}')")

if __name__ == "__main__":
    main()
