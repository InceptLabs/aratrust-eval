#!/usr/bin/env python3
"""Investigate Ethics regression using CSV data."""

import pandas as pd

# Load the CSV (this is Run 2 data)
df = pd.read_csv("/Users/ahmedabulkhair/Documents/Safety & Alignment /AraTrust/aratrust-eval/results/eval_v1.0_zero_shot.csv")

# Broken Ethics samples (correct in Run 1, wrong in Run 2)
broken_samples = [89, 102, 112, 119]

print("="*80)
print("INVESTIGATING ETHICS REGRESSION - BROKEN SAMPLES (From CSV)")
print("="*80)

for idx in broken_samples:
    sample = df[df['sample_idx'] == idx].iloc[0]

    print(f"\n{'='*80}")
    print(f"SAMPLE {idx}")
    print("="*80)

    print(f"\nCategory: {sample['category']}")
    print(f"Subcategory: {sample['subcategory']}")
    print(f"\nQuestion: {sample['question']}")
    print(f"\nChoices:")
    print(f"  أ) {sample['choice_a']}")
    print(f"  ب) {sample['choice_b']}")
    print(f"  ج) {sample['choice_c']}")
    print(f"\nCorrect Answer: {sample['correct_answer']}")
    print(f"Model Predicted: {sample['predicted']}")
    print(f"Is Correct: {sample['is_correct']}")

    print(f"\n--- RAW MODEL RESPONSE ---")
    raw = sample['raw_response']
    if pd.notna(raw) and raw:
        print(raw[:2000] if len(str(raw)) > 2000 else raw)
    else:
        print("(No raw response recorded)")

    print("\n" + "-"*40)

# Also show the fixed sample (was wrong in Run 1, correct in Run 2)
print(f"\n{'='*80}")
print("FIXED ETHICS SAMPLE (Sample 118)")
print("="*80)

sample = df[df['sample_idx'] == 118].iloc[0]
print(f"\nCategory: {sample['category']}")
print(f"Subcategory: {sample['subcategory']}")
print(f"\nQuestion: {sample['question']}")
print(f"\nChoices:")
print(f"  أ) {sample['choice_a']}")
print(f"  ب) {sample['choice_b']}")
print(f"  ج) {sample['choice_c']}")
print(f"\nCorrect Answer: {sample['correct_answer']}")
print(f"Model Predicted: {sample['predicted']}")
print(f"Is Correct: {sample['is_correct']}")

print(f"\n--- RAW MODEL RESPONSE ---")
raw = sample['raw_response']
if pd.notna(raw) and raw:
    print(raw[:2000] if len(str(raw)) > 2000 else raw)
else:
    print("(No raw response recorded)")

# Summary of all Ethics samples
print(f"\n{'='*80}")
print("ETHICS CATEGORY SUMMARY")
print("="*80)

ethics_df = df[df['category'] == 'Ethics']
print(f"\nTotal Ethics samples: {len(ethics_df)}")
print(f"Correct: {ethics_df['is_correct'].sum()}")
print(f"Incorrect: {len(ethics_df) - ethics_df['is_correct'].sum()}")
print(f"Accuracy: {ethics_df['is_correct'].mean()*100:.2f}%")

print(f"\nBy Subcategory:")
for subcat in ethics_df['subcategory'].unique():
    sub_df = ethics_df[ethics_df['subcategory'] == subcat]
    acc = sub_df['is_correct'].mean() * 100
    print(f"  {subcat}: {sub_df['is_correct'].sum()}/{len(sub_df)} ({acc:.1f}%)")

print(f"\nIncorrect Ethics samples:")
incorrect = ethics_df[ethics_df['is_correct'] == False]
for _, row in incorrect.iterrows():
    print(f"  Sample {row['sample_idx']}: {row['subcategory']} - predicted '{row['predicted']}', correct '{row['correct_answer']}'")
