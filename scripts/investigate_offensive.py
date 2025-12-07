#!/usr/bin/env python3
"""Investigate Offensive category - the weakest category."""

import pandas as pd
from collections import Counter

# Load the CSV (Run 2 data)
df = pd.read_csv("/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval/results/eval_v1.0_zero_shot.csv")

print("="*80)
print("OFFENSIVE CATEGORY DEEP DIVE")
print("="*80)

# Filter for Offensive category
offensive_df = df[df['category'] == 'Offensive']

print(f"\nTotal Offensive samples: {len(offensive_df)}")
print(f"Correct: {offensive_df['is_correct'].sum()}")
print(f"Incorrect: {len(offensive_df) - offensive_df['is_correct'].sum()}")
print(f"Accuracy: {offensive_df['is_correct'].mean()*100:.2f}%")

# By subcategory
print(f"\n{'='*80}")
print("BY SUBCATEGORY")
print("="*80)

print(f"\n{'Subcategory':<30} {'Total':>8} {'Correct':>8} {'Incorrect':>8} {'Accuracy':>10}")
print("-" * 70)

for subcat in sorted(offensive_df['subcategory'].unique()):
    sub_df = offensive_df[offensive_df['subcategory'] == subcat]
    correct = sub_df['is_correct'].sum()
    total = len(sub_df)
    acc = correct / total * 100
    print(f"{subcat:<30} {total:>8} {correct:>8} {total-correct:>8} {acc:>9.2f}%")

# Analyze incorrect samples
print(f"\n{'='*80}")
print("ALL INCORRECT OFFENSIVE SAMPLES (23)")
print("="*80)

incorrect = offensive_df[offensive_df['is_correct'] == False].sort_values('sample_idx')

for _, row in incorrect.iterrows():
    print(f"\n{'-'*80}")
    print(f"SAMPLE {row['sample_idx']} | Subcategory: {row['subcategory']}")
    print("-"*80)
    print(f"\nQuestion: {row['question']}")
    print(f"\nChoices:")
    print(f"  أ) {row['choice_a']}")
    print(f"  ب) {row['choice_b']}")
    print(f"  ج) {row['choice_c']}")
    print(f"\nCorrect Answer: {row['correct_answer']}")
    print(f"Model Predicted: {row['predicted']}")

    # Show truncated raw response
    raw = row['raw_response']
    if pd.notna(raw) and raw:
        print(f"\nRaw Response (first 800 chars):")
        print(str(raw)[:800] + "..." if len(str(raw)) > 800 else raw)

# Pattern analysis
print(f"\n{'='*80}")
print("PATTERN ANALYSIS")
print("="*80)

# Prediction patterns in incorrect samples
print("\nIncorrect Prediction Patterns:")
pred_patterns = Counter()
for _, row in incorrect.iterrows():
    pattern = f"Predicted '{row['predicted']}' instead of '{row['correct_answer']}'"
    pred_patterns[pattern] += 1

for pattern, count in pred_patterns.most_common():
    print(f"  {pattern}: {count} times")

# Subcategory error distribution
print("\nErrors by Subcategory:")
subcat_errors = Counter(incorrect['subcategory'])
for subcat, count in subcat_errors.most_common():
    total = len(offensive_df[offensive_df['subcategory'] == subcat])
    print(f"  {subcat}: {count}/{total} incorrect ({count/total*100:.1f}% error rate)")

# Check if there's a bias towards certain answers
print("\nAnswer Distribution in Incorrect Samples:")
print(f"  Correct answers that were missed: {Counter(incorrect['correct_answer'])}")
print(f"  Wrong predictions made: {Counter(incorrect['predicted'])}")
