"""
Direct evaluation function for The Agent Company green agent.

This module provides a simple, direct API for running evaluations
without needing to go through the A2A protocol.
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path

from .evaluator import TACEvaluator
from .task_selector import TaskSelector, parse_task_config


async def evaluate_agent(
    white_agent_url: str,
    task_subset: Optional[str] = None,
    task_names: Optional[List[str]] = None,
    max_tasks: Optional[int] = None,
    random_seed: Optional[int] = None,
    server_hostname: Optional[str] = None,
    output_dir: Optional[str] = None,
    env_llm_config: Optional[Dict[str, str]] = None,
    use_host_network: bool = True,
) -> Dict[str, Any]:
    """
    Direct evaluation function for evaluating a white agent.
    
    This is a convenience function that wraps TACEvaluator and provides
    a simpler API for running evaluations programmatically.
    
    Args:
        white_agent_url: URL of the white agent to evaluate
        task_subset: Name of predefined subset (e.g., "beginner", "intermediate", "advanced")
        task_names: Specific task names to evaluate (overrides task_subset)
        max_tasks: Maximum number of tasks to evaluate
        random_seed: Random seed for reproducible task selection
        server_hostname: Hostname where TAC services are running (default: "localhost")
        output_dir: Directory to save evaluation results (default: temp directory)
        env_llm_config: Environment LLM configuration dict with keys:
            - api_key: LLM API key
            - base_url: LLM base URL (optional)
            - model: LLM model name (default: "openai/gpt-4o")
        use_host_network: Whether to use Docker host networking (default: True)
    
    Returns:
        Dictionary containing evaluation results with keys:
            - summary: Aggregated summary with total_score, total_possible, overall_score, etc.
            - tasks: List of individual task results
            - total_time: Total evaluation time in seconds
            - output_dir: Directory where results were saved
    
    Example:
        ```python
        import asyncio
        from src.green_agent.evaluation.evaluation_function import evaluate_agent
        
        async def main():
            results = await evaluate_agent(
                white_agent_url="http://localhost:9002",
                task_subset="beginner",
                max_tasks=3,
                env_llm_config={
                    "api_key": "your-api-key",
                    "model": "openai/gpt-4o"
                }
            )
            print(f"Overall score: {results['summary']['overall_score']:.2%}")
        
        asyncio.run(main())
        ```
    """
    # Set defaults from environment variables if not provided
    if server_hostname is None:
        server_hostname = os.getenv("SERVER_HOSTNAME", "localhost")
    
    if env_llm_config is None:
        env_llm_config = {
            "api_key": os.getenv("LITELLM_API_KEY", ""),
            "base_url": os.getenv("LITELLM_BASE_URL", ""),
            "model": os.getenv("LITELLM_MODEL", "openai/gpt-4o"),
        }
    
    # Create task selector
    task_selector = TaskSelector(
        subset=task_subset,
        task_names=task_names,
        max_tasks=max_tasks,
        random_seed=random_seed,
    )
    
    # Create evaluator
    evaluator = TACEvaluator(
        white_agent_url=white_agent_url,
        server_hostname=server_hostname,
        env_llm_config=env_llm_config,
        output_dir=output_dir,
        use_host_network=use_host_network,
    )
    
    # Run evaluation
    results = await evaluator.evaluate_tasks(task_selector)
    
    return results


def evaluate_agent_sync(
    white_agent_url: str,
    task_subset: Optional[str] = None,
    task_names: Optional[List[str]] = None,
    max_tasks: Optional[int] = None,
    random_seed: Optional[int] = None,
    server_hostname: Optional[str] = None,
    output_dir: Optional[str] = None,
    env_llm_config: Optional[Dict[str, str]] = None,
    use_host_network: bool = True,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for evaluate_agent.
    
    This function runs the async evaluate_agent in an event loop,
    making it easier to use in synchronous code.
    
    Args:
        Same as evaluate_agent()
    
    Returns:
        Same as evaluate_agent()
    
    Example:
        ```python
        from src.green_agent.evaluation.evaluation_function import evaluate_agent_sync
        
        results = evaluate_agent_sync(
            white_agent_url="http://localhost:9002",
            task_subset="beginner",
            max_tasks=3
        )
        print(f"Overall score: {results['summary']['overall_score']:.2%}")
        ```
    """
    return asyncio.run(evaluate_agent(
        white_agent_url=white_agent_url,
        task_subset=task_subset,
        task_names=task_names,
        max_tasks=max_tasks,
        random_seed=random_seed,
        server_hostname=server_hostname,
        output_dir=output_dir,
        env_llm_config=env_llm_config,
        use_host_network=use_host_network,
    ))


def save_evaluation_results(results: Dict[str, Any], output_file: str) -> None:
    """
    Save evaluation results to a JSON file.
    
    Args:
        results: Evaluation results dictionary from evaluate_agent()
        output_file: Path to output JSON file
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Evaluation results saved to: {output_file}")


def print_evaluation_summary(results: Dict[str, Any]) -> None:
    """
    Print a formatted summary of evaluation results.
    
    Args:
        results: Evaluation results dictionary from evaluate_agent()
    """
    summary = results.get("summary", {})
    tasks = results.get("tasks", [])
    total_time = results.get("total_time", 0)
    
    print("\n" + "="*60)
    print("EVALUATION RESULTS")
    print("="*60)
    print()
    print(f"Total Tasks: {summary.get('total_tasks', 0)}")
    print(f"Completed: {summary.get('completed', 0)}")
    print(f"Failed: {summary.get('failed', 0)}")
    print()
    print(f"Overall Score: {summary.get('total_score', 0)}/{summary.get('total_possible', 0)}")
    print(f"Score Percentage: {summary.get('overall_score', 0.0)*100:.1f}%")
    print(f"Total Time: {total_time:.1f}s")
    print()
    print("Task Details:")
    print("-"*60)
    
    for task in tasks:
        task_name = task.get("task_name", "unknown")
        status = task.get("status", "unknown")
        elapsed = task.get("elapsed_time", 0)
        
        if status == "completed":
            eval_result = task.get("evaluation", {})
            final_score = eval_result.get("final_score", {})
            score = final_score.get("result", 0)
            total = final_score.get("total", 0)
            print(f"  ✓ {task_name}: {score}/{total} ({elapsed:.1f}s)")
        elif status == "failed":
            error = task.get("error", "Unknown error")
            print(f"  ✗ {task_name}: FAILED - {error} ({elapsed:.1f}s)")
        else:
            print(f"  ? {task_name}: {status}")
    
    print("="*60)
    print()
    
    if "output_dir" in results:
        print(f"Results saved in: {results['output_dir']}")

