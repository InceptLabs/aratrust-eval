"""AraTrust evaluation pipeline using LangGraph."""

from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END
import pandas as pd
import uuid
from datetime import datetime
import time
import asyncio

from .config import Config
from .data_loader import AraTrustLoader
from .prompt_templates import format_prompt
from .llm_client import LMStudioClient, FireworksClient, AsyncFireworksClient

# Try to import Langfuse, make it optional
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False


class EvaluationState(TypedDict):
    """State for the evaluation graph"""

    samples: List[dict]
    current_idx: int
    results: List[dict]
    model_version: str
    prompt_type: str
    use_chat: bool


class AraTrustEvaluator:
    def __init__(self, use_langfuse: bool = True):
        self.config = Config()
        self.use_langfuse = use_langfuse and LANGFUSE_AVAILABLE

        # Initialize Langfuse if available and configured
        self.langfuse = None
        if self.use_langfuse:
            try:
                self.langfuse = Langfuse(
                    host=self.config.LANGFUSE_HOST,
                    public_key=self.config.LANGFUSE_PUBLIC_KEY,
                    secret_key=self.config.LANGFUSE_SECRET_KEY,
                )
                # Test connection
                self.langfuse.auth_check()
                print("Langfuse connected successfully")
            except Exception as e:
                print(f"Langfuse connection failed: {e}")
                print("Continuing without Langfuse tracking...")
                self.langfuse = None
                self.use_langfuse = False

        # Initialize LLM client (Fireworks or LM Studio)
        self.async_client = None
        if self.config.USE_FIREWORKS:
            print(f"Using Fireworks AI with model: {self.config.MODEL_NAME}")
            print(f"Parallel workers: {self.config.NUM_WORKERS}")
            self.llm_client = FireworksClient(
                api_key=self.config.FIREWORKS_API_KEY,
                base_url=self.config.FIREWORKS_BASE_URL,
                model_name=self.config.MODEL_NAME,
            )
            # Also create async client for parallel evaluation
            self.async_client = AsyncFireworksClient(
                api_key=self.config.FIREWORKS_API_KEY,
                base_url=self.config.FIREWORKS_BASE_URL,
                model_name=self.config.MODEL_NAME,
            )
        else:
            print(f"Using LM Studio with model: {self.config.MODEL_NAME}")
            self.llm_client = LMStudioClient(
                base_url=self.config.LM_STUDIO_BASE_URL,
                model_name=self.config.MODEL_NAME,
            )

        self.data_loader = AraTrustLoader()

        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph evaluation pipeline"""

        workflow = StateGraph(EvaluationState)

        # Add nodes
        workflow.add_node("load_data", self.load_data_node)
        workflow.add_node("evaluate_sample", self.evaluate_sample_node)
        workflow.add_node("aggregate_results", self.aggregate_results_node)

        # Add edges
        workflow.set_entry_point("load_data")
        workflow.add_edge("load_data", "evaluate_sample")
        workflow.add_conditional_edges(
            "evaluate_sample",
            self.should_continue,
            {"continue": "evaluate_sample", "done": "aggregate_results"},
        )
        workflow.add_edge("aggregate_results", END)

        return workflow.compile()

    # =========================================================================
    # Helper Methods - Shared logic for sync and async evaluation
    # =========================================================================

    def _process_sample(self, sample: dict, prompt_type: str) -> tuple:
        """Extract and format sample data.

        Args:
            sample: Raw sample dict from dataset
            prompt_type: Prompt type for formatting

        Returns:
            Tuple of (prompt, correct_answer, category, subcategory, sample_data)
        """
        question = sample.get("Question", "")
        choice_a = sample.get("A", "")
        choice_b = sample.get("B", "")
        choice_c = sample.get("C", "")
        correct_answer = sample.get("Answer", "")
        category = sample.get("Category", "unknown")
        subcategory = sample.get("Subcategory", "")

        prompt = format_prompt(
            question=question,
            choice_a=choice_a,
            choice_b=choice_b,
            choice_c=choice_c,
            prompt_type=prompt_type,
        )

        sample_data = {
            "question": str(question),
            "choice_a": str(choice_a),
            "choice_b": str(choice_b),
            "choice_c": str(choice_c),
        }

        return prompt, correct_answer, category, subcategory, sample_data

    def _create_eval_result(
        self,
        idx: int,
        result: Dict[str, Any],
        latency_ms: int,
        sample_data: Dict[str, str],
        correct_answer: str,
        category: str,
        subcategory: str,
        prompt_type: str,
    ) -> dict:
        """Create standardized evaluation result.

        Args:
            idx: Sample index
            result: LLM response dict
            latency_ms: Response latency in milliseconds
            sample_data: Dict with question and choices
            correct_answer: Expected answer
            category: Sample category
            subcategory: Sample subcategory
            prompt_type: Prompt type used

        Returns:
            Standardized evaluation result dict
        """
        predicted = result.get("predicted_choice", "")
        is_correct = predicted == correct_answer
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return {
            "sample_idx": idx,
            "timestamp": datetime.now().isoformat(),
            "model": self.config.MODEL_NAME,
            "prompt_type": prompt_type,
            "category": category,
            "subcategory": subcategory,
            **sample_data,
            "correct_answer": correct_answer,
            "predicted": predicted,
            "is_correct": is_correct,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "raw_response": result.get("raw_response", ""),
            "trace_id": str(uuid.uuid4()),
            "error": result.get("error"),
        }

    def _log_to_langfuse(
        self,
        prompt: str,
        result: Dict[str, Any],
        eval_result: dict,
        model_version: str,
        prompt_type: str,
    ) -> None:
        """Log evaluation to Langfuse.

        Args:
            prompt: The input prompt
            result: LLM response dict
            eval_result: Evaluation result dict
            model_version: Model version string
            prompt_type: Prompt type used
        """
        if not self.langfuse:
            return

        try:
            trace = self.langfuse.trace(
                name="aratrust_eval",
                session_id=getattr(self, "_session_id", None),
                tags=getattr(self, "_tags", []),
                input={"prompt": prompt},
                output={
                    "response": result.get("raw_response", ""),
                    "predicted": eval_result["predicted"],
                },
                metadata={
                    "model_version": model_version,
                    "prompt_type": prompt_type,
                    "sample_idx": eval_result["sample_idx"],
                    "category": eval_result["category"],
                    "subcategory": eval_result["subcategory"],
                    "correct_answer": eval_result["correct_answer"],
                    "is_correct": eval_result["is_correct"],
                },
            )
            generation = trace.generation(
                name="mcq_response",
                model=self.config.MODEL_NAME,
                input=[{"role": "user", "content": prompt}],
                output=result.get("raw_response", ""),
                metadata={
                    "correct_answer": eval_result["correct_answer"],
                    "is_correct": eval_result["is_correct"],
                },
            )
            generation.end()
        except Exception:
            pass  # Silent fail for logging

    def _aggregate_and_save_results(
        self,
        results: List[dict],
        samples: List[dict],
        model_version: str,
        prompt_type: str,
    ) -> None:
        """Aggregate results and save to CSV.

        Args:
            results: List of evaluation result dicts
            samples: List of sample dicts (for count)
            model_version: Model version string
            prompt_type: Prompt type used
        """
        results_df = pd.DataFrame(results)
        overall_accuracy = results_df["is_correct"].mean()
        category_accuracy = results_df.groupby("category")["is_correct"].mean()
        error_count = results_df["error"].notna().sum()

        print("\n" + "=" * 50)
        print("EVALUATION RESULTS")
        print("=" * 50)
        print(f"Model: {model_version}")
        print(f"Prompt Type: {prompt_type}")
        print(f"Total Samples: {len(samples)}")
        print(f"Errors: {error_count}")
        print(f"\nOverall Accuracy: {overall_accuracy:.2%}")
        print("\nPer-Category Accuracy:")
        for cat, acc in category_accuracy.items():
            print(f"  {cat}: {acc:.2%}")
        print("=" * 50)

        output_file = f"results/eval_{model_version}_{prompt_type}.csv"
        results_df.to_csv(output_file, index=False)
        print(f"\nResults saved to: {output_file}")

    # =========================================================================
    # LangGraph Nodes - Sequential evaluation
    # =========================================================================

    def load_data_node(self, state: EvaluationState) -> dict:
        """Load AraTrust dataset"""
        df = self.data_loader.load()

        # Explore schema on first load
        self.data_loader.explore_schema()

        # Convert to list of dicts
        samples = df.to_dict("records")

        # Apply limit if set
        if hasattr(self, "_limit") and self._limit:
            samples = samples[: self._limit]
            print(f"Limited to {len(samples)} samples for testing")

        return {"samples": samples, "current_idx": 0, "results": []}

    def evaluate_sample_node(self, state: EvaluationState) -> dict:
        """Evaluate a single sample"""
        idx = state["current_idx"]
        sample = state["samples"][idx]

        # Process sample using helper
        prompt, correct_answer, category, subcategory, sample_data = (
            self._process_sample(sample, state["prompt_type"])
        )

        # Get prediction with timing
        start_time = time.time()
        if state.get("use_chat", False):
            result = self.llm_client.get_chat_completion(prompt)
        else:
            result = self.llm_client.get_completion(prompt)
        latency_ms = int((time.time() - start_time) * 1000)

        # Create eval result using helper
        eval_result = self._create_eval_result(
            idx=idx,
            result=result,
            latency_ms=latency_ms,
            sample_data=sample_data,
            correct_answer=correct_answer,
            category=category,
            subcategory=subcategory,
            prompt_type=state["prompt_type"],
        )

        # Log to Langfuse using helper
        self._log_to_langfuse(
            prompt=prompt,
            result=result,
            eval_result=eval_result,
            model_version=state["model_version"],
            prompt_type=state["prompt_type"],
        )

        # Print progress
        status = "✓" if eval_result["is_correct"] else "✗"
        print(
            f"[{idx + 1}/{len(state['samples'])}] {status} Predicted: {eval_result['predicted']}, Correct: {correct_answer}"
        )

        return {"current_idx": idx + 1, "results": state["results"] + [eval_result]}

    def should_continue(self, state: EvaluationState) -> str:
        """Check if we should continue evaluating"""
        if state["current_idx"] >= len(state["samples"]):
            return "done"
        return "continue"

    def aggregate_results_node(self, state: EvaluationState) -> dict:
        """Aggregate and report results"""
        self._aggregate_and_save_results(
            results=state["results"],
            samples=state["samples"],
            model_version=state["model_version"],
            prompt_type=state["prompt_type"],
        )
        return state

    # =========================================================================
    # Async Evaluation - Parallel execution for Fireworks AI
    # =========================================================================

    async def _evaluate_single_sample_async(
        self, idx: int, sample: dict, model_version: str, prompt_type: str
    ) -> dict:
        """Async evaluation of a single sample"""
        # Process sample using helper
        prompt, correct_answer, category, subcategory, sample_data = (
            self._process_sample(sample, prompt_type)
        )

        start_time = time.time()
        result = await self.async_client.get_chat_completion(prompt)
        latency_ms = int((time.time() - start_time) * 1000)

        # Create eval result using helper
        eval_result = self._create_eval_result(
            idx=idx,
            result=result,
            latency_ms=latency_ms,
            sample_data=sample_data,
            correct_answer=correct_answer,
            category=category,
            subcategory=subcategory,
            prompt_type=prompt_type,
        )

        # Log to Langfuse using helper
        self._log_to_langfuse(
            prompt=prompt,
            result=result,
            eval_result=eval_result,
            model_version=model_version,
            prompt_type=prompt_type,
        )

        return eval_result

    async def _run_parallel_evaluation(
        self, samples: List[dict], model_version: str, prompt_type: str
    ) -> List[dict]:
        """Run evaluation in parallel using asyncio"""
        num_workers = self.config.NUM_WORKERS
        semaphore = asyncio.Semaphore(num_workers)
        completed = 0
        total = len(samples)

        async def bounded_eval(idx: int, sample: dict) -> dict:
            nonlocal completed
            async with semaphore:
                result = await self._evaluate_single_sample_async(
                    idx, sample, model_version, prompt_type
                )
                completed += 1
                status = "✓" if result["is_correct"] else "✗"
                print(
                    f"[{completed}/{total}] {status} Predicted: {result['predicted']}, Correct: {result['correct_answer']}"
                )
                return result

        tasks = [bounded_eval(i, s) for i, s in enumerate(samples)]
        results = await asyncio.gather(*tasks)
        return list(results)

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    def run(
        self,
        model_version: str = "v1.0",
        prompt_type: str = "zero_shot",
        use_chat: bool = False,
        limit: Optional[int] = None,
        run_id: Optional[str] = None,
    ) -> dict:
        """Run the evaluation"""

        # Store limit for use in load_data_node
        self._limit = limit

        # Set up run_id for Langfuse session and tags
        if not run_id:
            run_id = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._run_id = run_id
        self._session_id = run_id
        model_short_name = self.config.MODEL_NAME.split("/")[-1]
        self._tags = [run_id, model_short_name]

        print("\nStarting AraTrust evaluation...")
        print(f"Run ID: {run_id}")
        print(f"Model version: {model_version}")
        print(f"Prompt type: {prompt_type}")
        print(f"API mode: {'chat' if use_chat else 'completion'}")
        print(f"Langfuse tracking: {'enabled' if self.langfuse else 'disabled'}")
        if limit:
            print(f"Sample limit: {limit}")

        # Health check
        if not self.llm_client.health_check():
            if self.config.USE_FIREWORKS:
                raise RuntimeError(
                    "Fireworks AI is not accessible. Check your API key and network connection."
                )
            else:
                raise RuntimeError(
                    "LM Studio server is not available. Start LM Studio and enable the server."
                )

        # Use parallel evaluation for Fireworks AI
        if self.async_client:
            print(
                f"Running parallel evaluation with {self.config.NUM_WORKERS} workers..."
            )

            # Load data
            df = self.data_loader.load()
            self.data_loader.explore_schema()
            samples = df.to_dict("records")

            if limit:
                samples = samples[:limit]
                print(f"Limited to {len(samples)} samples for testing")

            # Run parallel evaluation
            results = asyncio.run(
                self._run_parallel_evaluation(samples, model_version, prompt_type)
            )

            # Aggregate and save using helper
            self._aggregate_and_save_results(
                results=results,
                samples=samples,
                model_version=model_version,
                prompt_type=prompt_type,
            )

            final_state = {"samples": samples, "results": results}
        else:
            # Sequential evaluation using LangGraph (for LM Studio)
            initial_state: EvaluationState = {
                "samples": [],
                "current_idx": 0,
                "results": [],
                "model_version": model_version,
                "prompt_type": prompt_type,
                "use_chat": use_chat,
            }
            final_state = self.graph.invoke(initial_state, {"recursion_limit": 1000})

        # Flush Langfuse if available
        if self.langfuse:
            self.langfuse.flush()

        return final_state
