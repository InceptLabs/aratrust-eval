import argparse
import sys
from .evaluator import AraTrustEvaluator


def main():
    parser = argparse.ArgumentParser(
        description="AraTrust Evaluation Pipeline - Evaluate Arabic LLMs on safety benchmarks"
    )
    parser.add_argument(
        "--model-version",
        type=str,
        default="v1.0",
        help="Model version identifier for tracking (default: v1.0)",
    )
    parser.add_argument(
        "--prompt-type",
        type=str,
        choices=["zero_shot", "one_shot"],
        default="zero_shot",
        help="Prompt type to use (default: zero_shot)",
    )
    parser.add_argument(
        "--use-chat",
        action="store_true",
        help="Use chat completions API instead of completions API",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit number of samples for testing"
    )
    parser.add_argument(
        "--explore-only",
        action="store_true",
        help="Only explore dataset schema, don't run evaluation",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Run identifier for Langfuse session and tags (auto-generated if not provided)",
    )
    parser.add_argument(
        "--export-incorrect",
        action="store_true",
        help="Export incorrect traces (is_correct=False) to a Langfuse dataset",
    )
    parser.add_argument(
        "--dataset-name",
        type=str,
        default="False_AraTrust",
        help="Dataset name for exporting incorrect traces (default: False_AraTrust)",
    )

    args = parser.parse_args()

    if args.explore_only:
        from .data_loader import AraTrustLoader

        loader = AraTrustLoader()
        df = loader.load()
        loader.explore_schema()

        print("\nCategory distribution:")
        dist = loader.get_category_distribution(df)
        for cat, count in dist.items():
            print(f"  {cat}: {count}")

        print(f"\nTotal samples: {len(df)}")
        sys.exit(0)

    if args.export_incorrect:
        if not args.run_id:
            print("Error: --run-id is required for --export-incorrect")
            sys.exit(1)

        from .dataset_utils import LangfuseDatasetManager

        manager = LangfuseDatasetManager()
        count = manager.export_incorrect_to_dataset(
            run_id=args.run_id, dataset_name=args.dataset_name
        )
        print(f"\nExport complete. {count} items added to '{args.dataset_name}'")
        sys.exit(0)

    try:
        evaluator = AraTrustEvaluator()
        evaluator.run(
            model_version=args.model_version,
            prompt_type=args.prompt_type,
            use_chat=args.use_chat,
            limit=args.limit,
            run_id=args.run_id,
        )
    except RuntimeError as e:
        print(f"\nError: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nEvaluation interrupted by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
