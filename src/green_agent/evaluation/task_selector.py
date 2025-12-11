"""Task selection logic for TAC evaluation."""

from typing import List, Dict, Optional
import random


# Curated task subsets - customize these!
TASK_SUBSETS = {
    "beginner": [
        "pm-send-hello-message",
        #"sde-create-new-repo",
        #"hr-check-attendance-one-day",
        #"finance-qualified-bill-ask-for-reimburse",
    ],
    "intermediate": [
        "pm-schedule-meeting-2",
        "sde-run-janusgraph",
        "sde-check-and-run-unit-test",
        "hr-new-grad-job-description-3",
        "ds-janusgraph-exercise",
    ],
    "advanced": [
        "sde-implement-raft-in-go",
        "sde-debug-crashed-server",
        "ds-predictive-modeling",
        "research-answer-questions-on-paper",
    ],
    "coding_focused": [
        "sde-create-new-repo",
        "sde-run-janusgraph",
        "sde-check-and-run-unit-test",
        "sde-implement-raft-in-go",
        "sde-debug-crashed-server",
        "ds-janusgraph-exercise",
    ],
    "communication_focused": [
        "pm-send-hello-message",
        "pm-schedule-meeting-2",
        "hr-check-attendance-one-day",
        "qa-escalate-emergency",
    ],
    "multi_service": [
        "pm-copy-plane-issues-to-gitlab",
        "pm-update-gitlab-issue-from-plane-status",
        "sde-report-unit-test-coverage-to-plane",
    ],
}


def get_task_image_name(task_name: str, version: str = "1.0.0") -> str:
    """Convert task name to Docker image name."""
    return f"ghcr.io/theagentcompany/{task_name}-image:{version}"


class TaskSelector:
    """Selects tasks for evaluation based on configuration."""
    
    def __init__(
        self,
        subset: Optional[str] = None,
        task_ids: Optional[List[int]] = None,
        task_names: Optional[List[str]] = None,
        max_tasks: Optional[int] = None,
        random_seed: Optional[int] = None,
    ):
        """
        Initialize task selector.
        
        Args:
            subset: Name of predefined subset (e.g., "beginner", "intermediate")
            task_ids: Specific task IDs to evaluate (if tasks are numbered)
            task_names: Specific task names to evaluate
            max_tasks: Maximum number of tasks to select
            random_seed: Random seed for reproducible selection
        """
        self.subset = subset
        self.task_ids = task_ids
        self.task_names = task_names
        self.max_tasks = max_tasks
        self.random_seed = random_seed
        
        if random_seed is not None:
            random.seed(random_seed)
    
    def select_tasks(self) -> List[str]:
        """
        Select tasks based on configuration.
        
        Returns:
            List of task names (without -image suffix)
        """
        if self.task_names:
            # Use explicitly provided task names
            tasks = self.task_names
        elif self.subset and self.subset in TASK_SUBSETS:
            # Use predefined subset
            tasks = TASK_SUBSETS[self.subset]
        else:
            # Default: use intermediate subset
            tasks = TASK_SUBSETS.get("intermediate", [])
        
        # Apply max_tasks limit
        if self.max_tasks and len(tasks) > self.max_tasks:
            tasks = random.sample(tasks, self.max_tasks)
        
        return tasks
    
    def get_task_images(self) -> List[str]:
        """Get Docker image names for selected tasks."""
        return [get_task_image_name(task) for task in self.select_tasks()]


def parse_task_config(config: Dict) -> TaskSelector:
    """
    Parse task configuration from evaluation config.
    
    Expected config format:
    {
        "task_subset": "intermediate",  # or None
        "task_ids": [1, 2, 3],          # or None
        "task_names": ["pm-schedule-meeting-1"],  # or None
        "max_tasks": 5,                 # or None
        "random_seed": 42               # or None
    }
    """
    return TaskSelector(
        subset=config.get("task_subset"),
        task_ids=config.get("task_ids"),
        task_names=config.get("task_names"),
        max_tasks=config.get("max_tasks"),
        random_seed=config.get("random_seed"),
    )

