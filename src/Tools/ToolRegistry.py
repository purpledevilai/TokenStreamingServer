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

from Tools.MemoryTools.append_memory import append_memory_tool
from Tools.MemoryTools.read_memory import read_memory_tool
from Tools.MemoryTools.view_memory_shape import view_memory_shape_tool
from Tools.MemoryTools.delete_memory import delete_memory_tool
from Tools.MemoryTools.write_memory import write_memory_tool

tool_registry = {
    # Pass Event Tool
    "pass_event": pass_event_tool,

    # Jira Tools
    "jira_create_issue": jira_create_issue_tool,
    "jira_search_issues": jira_search_issues_tool,
    "jira_update_issue": jira_update_issue_tool,
    "jira_transition_issue": jira_transition_issue_tool,
    "jira_assign_issue": jira_assign_issue_tool,
    "jira_unassign_issue": jira_unassign_issue_tool,
    "jira_get_sprints": jira_get_sprints_tool,
    "jira_get_sprint_issues": jira_get_sprint_issues_tool,

    # Memory Tools
    "append_memory": append_memory_tool,
    "read_memory": read_memory_tool,
    "view_memory_shape": view_memory_shape_tool,
    "delete_memory": delete_memory_tool,
    "write_memory": write_memory_tool,  
}
