"""Compare custom evaluation vs lm-evaluation-harness results"""

import pandas as pd
import json
import argparse
from pathlib import Path


def load_harness_results(json_path: str) -> dict:
    """Load results from lm-evaluation-harness output"""
    with open(json_path) as f:
        data = json.load(f)
    return data['results']['aratrust']


def load_custom_results(csv_path: str) -> dict:
    """Load results from custom evaluation CSV"""
    df = pd.read_csv(csv_path)
    return {
        'accuracy': df['is_correct'].mean(),
        'total': len(df),
        'correct': df['is_correct'].sum(),
        'per_category': df.groupby('category')['is_correct'].mean().to_dict()
    }


def compare_results(custom_csv: str, harness_json: str = None):
    """Compare custom evaluation results with optional harness results"""

    print("=" * 60)
    print("AraTrust Evaluation Results Comparison")
    print("=" * 60)

    # Load custom results
    custom = load_custom_results(custom_csv)
    print(f"\n[Custom Evaluation]")
    print(f"  Overall Accuracy: {custom['accuracy']*100:.2f}%")
    print(f"  Correct: {custom['correct']}/{custom['total']}")
    print(f"\n  Per Category:")
    for cat, acc in sorted(custom['per_category'].items()):
        print(f"    - {cat}: {acc*100:.2f}%")

    # Load harness results if provided
    if harness_json and Path(harness_json).exists():
        harness = load_harness_results(harness_json)
        print(f"\n[lm-evaluation-harness]")
        print(f"  Accuracy (acc):      {harness.get('acc', 0)*100:.2f}%")
        print(f"  Accuracy (acc_norm): {harness.get('acc_norm', 0)*100:.2f}%")

        print(f"\n[Comparison]")
        diff = custom['accuracy'] - harness.get('acc', 0)
        print(f"  Custom vs Harness: {diff*100:+.2f}%")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description='Compare AraTrust evaluation methods')
    parser.add_argument('custom_csv', help='Path to custom evaluation results CSV')
    parser.add_argument('--harness-json', help='Path to lm-evaluation-harness results JSON')

    args = parser.parse_args()
    compare_results(args.custom_csv, args.harness_json)


if __name__ == "__main__":
    main()
