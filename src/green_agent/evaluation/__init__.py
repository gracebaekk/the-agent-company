"""Evaluation modules for green agent."""

from .evaluator import TACEvaluator, parse_evaluation_request
from ...utils.docker_manager import DockerManager
from ...data.trajectory_collector import A2ATrajectoryCollector
from .task_selector import TaskSelector, parse_task_config, TASK_SUBSETS, get_task_image_name

# Scoring functions are available but may require TAC framework
try:
    from .scoring import (
        weighted_checkpoint_scoring,
        time_penalized_scoring,
        efficiency_scoring,
        composite_scoring,
    )
    __all__ = [
        "TACEvaluator",
        "parse_evaluation_request",
        "DockerManager",
        "A2ATrajectoryCollector",
        "TaskSelector",
        "parse_task_config",
        "TASK_SUBSETS",
        "get_task_image_name",
        "weighted_checkpoint_scoring",
        "time_penalized_scoring",
        "efficiency_scoring",
        "composite_scoring",
    ]
except ImportError:
    # Scoring functions not available (TAC framework not found)
    __all__ = [
        "TACEvaluator",
        "parse_evaluation_request",
        "DockerManager",
        "A2ATrajectoryCollector",
        "TaskSelector",
        "parse_task_config",
        "TASK_SUBSETS",
        "get_task_image_name",
    ]

