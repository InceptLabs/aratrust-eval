from datasets import load_dataset
from typing import Dict, Any
import pandas as pd


class AraTrustLoader:
    def __init__(self, dataset_name: str = "asas-ai/AraTrust"):
        self.dataset_name = dataset_name
        self.dataset = None
        self.categories = [
            "truthfulness",
            "ethics",
            "privacy",
            "illegal_activities",
            "mental_health",
            "physical_health",
            "unfairness",
            "offensive_language",
        ]

    def load(self, split: str = "test") -> pd.DataFrame:
        """Load AraTrust dataset"""
        print(f"Loading {self.dataset_name}...")
        self.dataset = load_dataset(self.dataset_name)

        # Get available splits
        available_splits = list(self.dataset.keys())
        print(f"Available splits: {available_splits}")

        # Use requested split or fall back to first available
        if split not in available_splits:
            split = available_splits[0]
            print(f"Using split: {split}")

        # Convert to DataFrame
        df = self.dataset[split].to_pandas()

        print(f"Loaded {len(df)} samples")
        print(f"Columns: {df.columns.tolist()}")

        return df

    def get_sample(self, idx: int, split: str = "test") -> Dict[str, Any]:
        """Get a single sample"""
        available_splits = list(self.dataset.keys())
        if split not in available_splits:
            split = available_splits[0]
        return self.dataset[split][idx]

    def explore_schema(self):
        """Print dataset schema for exploration"""
        if self.dataset is None:
            self.load()

        split = list(self.dataset.keys())[0]
        sample = self.dataset[split][0]

        print("\n" + "=" * 50)
        print("DATASET SCHEMA")
        print("=" * 50)
        print("\nSample structure:")
        for key, value in sample.items():
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            print(f"  {key}: {type(value).__name__} = {value_str}")
        print("=" * 50)

    def get_category_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Get distribution of samples per category"""
        if "category" in df.columns:
            return df["category"].value_counts().to_dict()
        return {}
