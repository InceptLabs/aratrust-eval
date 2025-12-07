"""Langfuse dataset utilities for managing evaluation results."""

from langfuse import Langfuse
from .config import Config


class LangfuseDatasetManager:
    """Manager for exporting traces to Langfuse datasets."""

    def __init__(self):
        self.config = Config()
        self.langfuse = Langfuse(
            host=self.config.LANGFUSE_HOST,
            public_key=self.config.LANGFUSE_PUBLIC_KEY,
            secret_key=self.config.LANGFUSE_SECRET_KEY,
        )

    def export_incorrect_to_dataset(
        self, run_id: str, dataset_name: str = "False_AraTrust"
    ) -> int:
        """
        Export traces with is_correct=False to a Langfuse dataset.

        Args:
            run_id: The run identifier (tag) to filter traces
            dataset_name: Name of the dataset to create/append to

        Returns:
            Number of items added to the dataset
        """
        print(f"Fetching traces with tag: {run_id}")

        # Fetch all traces with the run_id tag (paginated)
        all_traces = []
        page = 1
        while True:
            traces = self.langfuse.fetch_traces(tags=[run_id], limit=100, page=page)
            if not traces.data:
                break
            all_traces.extend(traces.data)
            print(f"  Fetched page {page}: {len(traces.data)} traces")
            page += 1

        print(f"Total traces fetched: {len(all_traces)}")

        # Filter for is_correct=False
        incorrect_traces = [
            t
            for t in all_traces
            if t.metadata and t.metadata.get("is_correct") is False
        ]
        print(f"Incorrect traces (is_correct=False): {len(incorrect_traces)}")

        if not incorrect_traces:
            print("No incorrect traces to export.")
            return 0

        # Create dataset if it doesn't exist
        try:
            self.langfuse.create_dataset(name=dataset_name)
            print(f"Created dataset: {dataset_name}")
        except Exception:
            print(f"Dataset '{dataset_name}' already exists, appending...")

        # Add traces as dataset items
        added_count = 0
        for trace in incorrect_traces:
            try:
                self.langfuse.create_dataset_item(
                    dataset_name=dataset_name,
                    input=trace.input,
                    expected_output=trace.metadata.get("correct_answer"),
                    metadata={
                        "trace_id": trace.id,
                        "category": trace.metadata.get("category"),
                        "subcategory": trace.metadata.get("subcategory"),
                        "predicted": trace.output.get("predicted")
                        if trace.output
                        else None,
                        "sample_idx": trace.metadata.get("sample_idx"),
                        "source_run_id": run_id,
                    },
                )
                added_count += 1
            except Exception as e:
                print(f"  Error adding item: {e}")

        print(f"Added {added_count} items to dataset '{dataset_name}'")

        # Flush to ensure all data is sent
        self.langfuse.flush()

        return added_count

    def list_datasets(self):
        """List all available datasets."""
        datasets = self.langfuse.get_datasets()
        print("Available datasets:")
        for ds in datasets:
            print(f"  - {ds.name}")
        return datasets
