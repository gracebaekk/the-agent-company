"""Task selection logic for TAC evaluation."""

from typing import List, Dict, Optional
import random

# current working tasks w/ full scores:
# "pm-send-hello-message",
# "sde-create-new-repo",
# "hr-check-attendance-one-day",
# "finance-qualified-bill-ask-for-reimburse"
# pm-distribute-information
# pm-change-channel-ownership
# pm-add-new-moderator
# pm-create-channel-new-leader
# pm-update-sprint-cycles

# pm-update-gitlab-issue-from-plane-status (1/3)
# pm-update-plane-issue-from-gitlab-status (1/7)
# pm-check-backlog-update-issues (1/5)
# pm-copy-plane-issues-to-gitlab (2/4)
# pm-create-teammate-channel-from-spreadsheet (1/5)

# All 175 TAC tasks organized by category
ALL_TASKS_BY_CATEGORY = {
    "admin": [
        "admin-arrange-meeting-rooms",
        "admin-ask-for-meeting-feedback",
        "admin-ask-for-upgrade-reimbursement",
        "admin-check-employees-budget-and-reply",
        "admin-check-employees-budget-and-reply-2",
        "admin-check-employees-budget-and-reply-and-record",
        "admin-collect-requests-and-compute-total-price",
        "admin-employee-info-reconciliation",
        "admin-get-best-vendor-quote",
        "admin-make-spreadsheet",
        "admin-mass-forms-filling",
        "admin-read-survey-and-summarise",
        "admin-remove-pages-pdf",
        "admin-translate-sales-chat",
        "admin-watch-video",
    ],
    "bm": [
        "bm-classify-nationality",
    ],
    "ds": [
        "ds-answer-numerical-data-question",
        "ds-answer-spreadsheet-questions",
        "ds-calculate-spreadsheet-stats",
        "ds-coffee-shop-database-management",
        "ds-find-meeting-spreadsheet",
        "ds-fix-table-values-and-missing-answers",
        "ds-format-excel-sheets",
        "ds-janusgraph-exercise",
        "ds-merge-multiple-sheets",
        "ds-organise-report-sus-data",
        "ds-predictive-modeling",
        "ds-sql-exercise",
        "ds-stock-analysis-slides",
        "ds-visualize-data-in-pie-and-bar-chart",
    ],
    "finance": [
        "finance-apply-tax-credit",
        "finance-budget-variance",
        "finance-check-attendance-payroll",
        "finance-create-10k-income-report",
        "finance-expense-validation",
        "finance-find-signatories",
        "finance-invoice-matching",
        "finance-nonqualified-bill-ask-for-reimburse",
        "finance-qualified-bill-ask-for-reimburse",
        "finance-r-d-activities",
        "finance-revenue-reconciliation",
        "finance-substantial-presence-test",
    ],
    "hr": [
        "hr-analyze-outing-bills",
        "hr-check-attendance-multiple-days",
        "hr-check-attendance-multiple-days-department",
        "hr-check-attendance-multiple-days-department-with-chat",
        "hr-check-attendance-one-day",
        "hr-check-for-invalid-passwords-and-ask-for-valid-passwords",
        "hr-collect-feedbacks",
        "hr-collect-multiple-valid-passwords",
        "hr-create-career-ladder",
        "hr-create-employee-manual",
        "hr-delete-and-insert-user",
        "hr-get-valid-password",
        "hr-green-card-consultation",
        "hr-internal-tooling-slides",
        "hr-make-slides-introduce-leadership",
        "hr-mass-survey",
        "hr-massive-resume-screening",
        "hr-new-grad-job-description",
        "hr-new-grad-job-description-2",
        "hr-new-grad-job-description-3",
        "hr-organize-talent-info",
        "hr-pick-interviewer-1",
        "hr-pick-interviewer-2",
        "hr-pick-interviewer-3",
        "hr-populate-salary-increase-memo",
        "hr-resume-categorization",
        "hr-resume-screening",
        "hr-salary-analysis",
        "hr-transfer-group",
    ],
    "ml": [
        "ml-generate-gradcam",
        "ml-grade-exam",
    ],
    "pm": [
        "pm-add-new-moderator",
        "pm-ask-for-issue-and-create-in-gitlab",
        "pm-ask-issue-assignee-for-issue-status-and-update-in-plane",
        "pm-assign-issues",
        "pm-change-channel-ownership",
        "pm-check-backlog-update-issues",
        "pm-copy-plane-issues-to-gitlab",
        "pm-create-channel-message",
        "pm-create-channel-message-medium",
        "pm-create-channel-new-leader",
        "pm-create-plane-issue",
        "pm-create-teammate-channel-from-spreadsheet",
        "pm-distribute-information",
        "pm-monitor-new-bug-issues",
        "pm-monthly-attendance-slides",
        "pm-plan-personnel-for-new-project",
        "pm-prepare-meeting-with-customers",
        "pm-present-engineer-group-members",
        "pm-present-gitlab-info-as-ppt",
        "pm-projects-analytics",
        "pm-schedule-meeting-1",
        "pm-schedule-meeting-2",
        "pm-send-hello-message",
        "pm-send-notification-to-corresponding-user",
        "pm-update-gitlab-issue-from-plane-status",
        "pm-update-plane-issue-from-gitlab-status",
        "pm-update-project-milestones",
        "pm-update-sprint-cycles",
    ],
    "qa": [
        "qa-escalate-emergency",
        "qa-update-issue-status-according-to-colleagues",
    ],
    "research": [
        "research-answer-questions-on-paper",
        "research-reproduce-figures",
    ],
    "sde": [
        "sde-add-all-repos-to-docs",
        "sde-add-one-gitlab-pipeline",
        "sde-add-wiki-page",
        "sde-change-branch-policy",
        "sde-change-license-easy",
        "sde-change-license-hard",
        "sde-check-and-run-unit-test",
        "sde-check-high-priority-issue",
        "sde-close-all-gitlab-issues",
        "sde-close-all-issue-on-all-project-under-tac-workspace",
        "sde-close-all-prs",
        "sde-close-an-issue",
        "sde-collect-open-issues",
        "sde-copilot-arena-server-easy-add-suffix",
        "sde-copilot-arena-server-new-endpoint",
        "sde-copilot-arena-server-setup",
        "sde-copy-issues-to-plane",
        "sde-copy-table-from-pdf-to-xlsx",
        "sde-create-commit-table-for-all-gitlab-users",
        "sde-create-new-characters",
        "sde-create-new-gitlab-project-logo",
        "sde-create-new-release",
        "sde-create-new-repo",
        "sde-create-sqlite-database",
        "sde-debug-crashed-server",
        "sde-delete-all-project-under-plane",
        "sde-delete-all-repos",
        "sde-delete-stale-branch",
        "sde-dependency-change-1",
        "sde-find-answer-in-codebase-1",
        "sde-find-answer-in-codebase-2",
        "sde-find-answer-in-codebase-3",
        "sde-find-api",
        "sde-fix-factual-mistake",
        "sde-fix-rising-wave-datatype",
        "sde-implement-buffer-pool-manager-bustub",
        "sde-implement-covering-index-in-janusgraph",
        "sde-implement-hyperloglog",
        "sde-implement-raft-in-go",
        "sde-install-go",
        "sde-install-openjdk",
        "sde-issue-label-management",
        "sde-migrate-package-manager",
        "sde-milestone-meeting",
        "sde-move-bustub-wiki",
        "sde-move-page-to-cloud",
        "sde-pitch-idea-to-manager",
        "sde-reply-community-issue-by-asking-npc",
        "sde-reply-community-issue-with-fixed-reply",
        "sde-repo_profile_pic",
        "sde-report-agent-repos",
        "sde-report-unit-test-coverage-to-plane",
        "sde-run-all-unit-test",
        "sde-run-janusgraph",
        "sde-run-linter-on-openhands",
        "sde-run-rising-wave-locally",
        "sde-sotopia-create-agent",
        "sde-sotopia-create-agent-wo-repo",
        "sde-sotopia-dev-container",
        "sde-sotopia-update-ci",
        "sde-summarize-recent-issues",
        "sde-sync-from-origin-repo",
        "sde-troubleshoot-dev-setup",
        "sde-update-dev-document",
        "sde-update-issue-status-on-plane",
        "sde-update-readme",
        "sde-write-a-unit-test-for-append_file-function",
        "sde-write-a-unit-test-for-scroll_down-function",
        "sde-write-a-unit-test-for-search_file-function",
    ],
    "example": [
        "example",
    ],
}

# Get all tasks as a flat list
ALL_TASKS = []
for category_tasks in ALL_TASKS_BY_CATEGORY.values():
    ALL_TASKS.extend(category_tasks)

# Curated task subsets - customize these!
TASK_SUBSETS = {
    "beginner": [
        "pm-send-hello-message",
        "sde-create-new-repo",
        "hr-check-attendance-one-day",
        "finance-qualified-bill-ask-for-reimburse",
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
    # Category-based subsets
    "all_admin": ALL_TASKS_BY_CATEGORY["admin"],
    "all_bm": ALL_TASKS_BY_CATEGORY["bm"],
    "all_ds": ALL_TASKS_BY_CATEGORY["ds"],
    "all_finance": ALL_TASKS_BY_CATEGORY["finance"],
    "all_hr": ALL_TASKS_BY_CATEGORY["hr"],
    "all_ml": ALL_TASKS_BY_CATEGORY["ml"],
    "all_pm": ALL_TASKS_BY_CATEGORY["pm"],
    "all_qa": ALL_TASKS_BY_CATEGORY["qa"],
    "all_research": ALL_TASKS_BY_CATEGORY["research"],
    "all_sde": ALL_TASKS_BY_CATEGORY["sde"],
    "all": ALL_TASKS,  # All 175 tasks
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

