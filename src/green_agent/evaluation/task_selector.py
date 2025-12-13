"""Task selection logic for TAC evaluation."""

from typing import List, Dict, Optional

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
        "ml-generate-gradcam-visualization",
        "ml-get-best-k-value",
        "ml-identify-animals",
        "ml-important-feature",
        "ml-prediction-on-label",
        "ml-request-meeting-with-engine-team-lead",
        "ml-run-airflow-dag",
        "ml-split-dataset-and-present-distribution",
        "ml-train-classification-model-report-accuracy",
    ],
    "pm": [
        "pm-add-new-moderator",
        "pm-ask-for-issue-and-create-in-gitlab",
        "pm-change-channel-ownership",
        "pm-check-backlog-update-issues",
        "pm-copy-plane-issues-to-gitlab",
        "pm-create-channel-new-leader",
        "pm-create-channel-no-clue",
        "pm-distribute-information",
        "pm-present-engineer-group-members",
        "pm-present-gitlab-info",
        "pm-schedule-meeting-1",
        "pm-schedule-meeting-2",
        "pm-schedule-meeting-3",
        "pm-schedule-meeting-4",
        "pm-send-hello-message",
        "pm-update-gitlab-issue-from-plane-status",
        "pm-update-sprint-cycles",
    ],
    "qa": [
        "qa-escalate-emergency",
        "qa-update-issue-status",
    ],
    "research": [
        "research-answer-questions-on-paper",
        "research-reproduce-tables-and-find-performance",
    ],
    "sde": [
        "sde-add-wiki-page",
        "sde-change-branch-policy",
        "sde-check-and-run-unit-test",
        "sde-close-all-the-issue",
        "sde-copy-commit-to-new-branch",
        "sde-copy-issues-to-plane",
        "sde-create-new-repo",
        "sde-debug-crashed-server",
        "sde-delete-all-repos-of-user",
        "sde-delete-all-users",
        "sde-delete-specific-branch",
        "sde-find-answer-in-codebase-3",
        "sde-find-answer-in-codebase",
        "sde-find-largest-ship-count-commit",
        "sde-implement-covering-index",
        "sde-implement-raft-in-go",
        "sde-implement-tcp-server",
        "sde-install-openjdk-retry-test",
        "sde-move-page",
        "sde-pitch-idea-to-manager",
        "sde-repo-status-2-issues",
        "sde-report-agent-repos-in-gitlab",
        "sde-report-unit-test-coverage-to-plane",
        "sde-reproduce-bug",
        "sde-run-janusgraph",
        "sde-run-linter",
        "sde-search-codebase",
        "sde-set-repo-secret",
        "sde-sotopia-create-agent-repo",
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

# Helper functions (minimal - used by evaluator/agent)
def get_task_image_name(task_name: str, version: str = "1.0.0") -> str:
    """Convert task name to Docker image name."""
    return f"ghcr.io/theagentcompany/{task_name}-image:{version}"


class TaskSelector:
    """Simplified task selector."""
    
    def __init__(self, task_names: Optional[List[str]] = None, **kwargs):
        self.task_names = task_names or []
    
    def select_tasks(self) -> List[str]:
        return self.task_names
    
    def get_task_images(self) -> List[str]:
        return [get_task_image_name(task) for task in self.select_tasks()]


def parse_task_config(config: Dict) -> TaskSelector:
    """Parse task configuration."""
    return TaskSelector(task_names=config.get("task_names", []))


# Legacy exports for compatibility
TASK_SUBSETS = {}
