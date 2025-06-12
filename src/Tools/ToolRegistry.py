from Tools.PassEvent import pass_event_tool
from Tools.JiraTools import (
    jira_create_issue_tool,
    jira_search_issues_tool,
    jira_update_issue_tool,
    jira_transition_issue_tool,
    jira_assign_issue_tool,
    jira_unassign_issue_tool,
    jira_get_sprints_tool,
    jira_get_sprint_issues_tool,
)

tool_registry = {
    "pass_event": pass_event_tool,
    "jira_create_issue": jira_create_issue_tool,
    "jira_search_issues": jira_search_issues_tool,
    "jira_update_issue": jira_update_issue_tool,
    "jira_transition_issue": jira_transition_issue_tool,
    "jira_assign_issue": jira_assign_issue_tool,
    "jira_unassign_issue": jira_unassign_issue_tool,
    "jira_get_sprints": jira_get_sprints_tool,
    "jira_get_sprint_issues": jira_get_sprint_issues_tool,
}
