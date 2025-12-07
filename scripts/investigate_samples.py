#!/usr/bin/env python3
"""Investigate specific samples from Langfuse traces."""

import sys
sys.path.insert(0, "/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval")

from langfuse import Langfuse
from src.config import Config

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

def get_sample_details(traces, sample_indices, category=None):
    """Get detailed information for specific sample indices."""
    results = {}
    for trace in traces:
        if trace.metadata:
            idx = trace.metadata.get("sample_idx")
            cat = trace.metadata.get("category")
            if idx in sample_indices and (category is None or cat == category):
                # Fetch full trace with observations/generations
                full_trace = langfuse.fetch_trace(trace.id)

                # Find generation observation
                raw_response = None
                if full_trace and hasattr(full_trace, 'data') and full_trace.data:
                    trace_data = full_trace.data
                    if hasattr(trace_data, 'observations') and trace_data.observations:
                        for obs in trace_data.observations:
                            if obs.type == "GENERATION":
                                raw_response = obs.output
                                break

                results[idx] = {
                    "trace_id": trace.id,
                    "category": cat,
                    "subcategory": trace.metadata.get("subcategory"),
                    "correct_answer": trace.metadata.get("correct_answer"),
                    "predicted": trace.output.get("predicted") if trace.output else None,
                    "is_correct": trace.metadata.get("is_correct"),
                    "input": trace.input,
                    "raw_response": raw_response or (trace.output.get("raw_response") if trace.output else None),
                }
    return results

def compare_sample_across_runs(run1_traces, run2_traces, sample_idx, category=None):
    """Compare a specific sample across two runs."""
    run1_sample = get_sample_details(run1_traces, [sample_idx], category).get(sample_idx)
    run2_sample = get_sample_details(run2_traces, [sample_idx], category).get(sample_idx)

    return run1_sample, run2_sample

def main():
    print("="*80)
    print("INVESTIGATING ETHICS REGRESSION - BROKEN SAMPLES")
    print("="*80)

    # Broken Ethics samples (correct in Run 1, wrong in Run 2)
    broken_samples = [89, 102, 112, 119]

    print("\nFetching traces...")
    all_traces = fetch_all_traces()

    # Group by session
    from collections import defaultdict
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

    print("\n" + "="*80)
    print("DETAILED ANALYSIS OF BROKEN ETHICS SAMPLES")
    print("="*80)

    for sample_idx in broken_samples:
        print(f"\n{'='*80}")
        print(f"SAMPLE {sample_idx}")
        print("="*80)

        run1_sample, run2_sample = compare_sample_across_runs(
            run1_traces, run2_traces, sample_idx, "Ethics"
        )

        if run1_sample:
            print(f"\n--- RUN 1 (CORRECT) ---")
            print(f"Subcategory: {run1_sample['subcategory']}")
            print(f"Correct Answer: {run1_sample['correct_answer']}")
            print(f"Predicted: {run1_sample['predicted']}")
            print(f"Is Correct: {run1_sample['is_correct']}")
            print(f"\nInput (Question):")
            if isinstance(run1_sample['input'], dict):
                print(run1_sample['input'].get('prompt', run1_sample['input']))
            else:
                print(run1_sample['input'])
            print(f"\nRaw Response (truncated):")
            raw = run1_sample.get('raw_response', '')
            if raw:
                print(raw[:500] + "..." if len(raw) > 500 else raw)

        if run2_sample:
            print(f"\n--- RUN 2 (INCORRECT) ---")
            print(f"Subcategory: {run2_sample['subcategory']}")
            print(f"Correct Answer: {run2_sample['correct_answer']}")
            print(f"Predicted: {run2_sample['predicted']}")
            print(f"Is Correct: {run2_sample['is_correct']}")
            print(f"\nRaw Response (truncated):")
            raw = run2_sample.get('raw_response', '')
            if raw:
                print(raw[:500] + "..." if len(raw) > 500 else raw)

        print("\n" + "-"*40)
        if run1_sample and run2_sample:
            print(f"CHANGE: {run1_sample['predicted']} (correct) → {run2_sample['predicted']} (incorrect)")

if __name__ == "__main__":
    main()
