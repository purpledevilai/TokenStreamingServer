from pydantic import BaseModel, Field
from LLM.AgentChat import AgentTool
from Models import User
from Services import JiraService
import json


class JiraCreateIssueParams(BaseModel):
    """
    Create a new Jira issue with specified details.
    Use this tool when you need to create a task, bug, story or other issue type in a Jira project.
    The issue will be created in the specified project with the provided summary and description.
    """
    project_key: str = Field(description="Key of the Jira project (e.g., 'PROJ', 'DEV')")
    summary: str = Field(description="Brief summary or title of the issue")
    description: str = Field(description="Detailed description of the issue, can include markdown formatting")
    issue_type: str = Field(default="Task", description="Type of the issue (e.g., 'Task', 'Bug', 'Story', 'Epic')")


def jira_create_issue_func(project_key: str, summary: str, description: str, issue_type: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        issue_data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"name": issue_type},
            }
        }
        res = JiraService.create_issue(user, issue_data)
        return json.dumps(res)
    except Exception as e:
        return f"Error creating issue: {e}"


jira_create_issue_tool = AgentTool(params=JiraCreateIssueParams, function=jira_create_issue_func, pass_context=True)


class JiraSearchIssuesParams(BaseModel):
    """
    Search for Jira issues using JQL (Jira Query Language).
    Use this tool to find existing issues matching specific criteria.
    Results will include issue keys, summaries, and other basic information.
    
    Example JQL queries:
    - project = "PROJ" AND status = "Open"
    - assignee = currentUser() AND resolution = Unresolved
    - created >= -30d AND project = "DEV"
    """
    jql: str = Field(description="Jira Query Language string to search issues (e.g., 'project = PROJ AND status = \"In Progress\"')")


def jira_search_issues_func(jql: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.search_issues(user, jql=jql)
        return json.dumps(res)
    except Exception as e:
        return f"Error searching issues: {e}"


jira_search_issues_tool = AgentTool(params=JiraSearchIssuesParams, function=jira_search_issues_func, pass_context=True)


class JiraUpdateIssueParams(BaseModel):
    """
    Update an existing Jira issue's summary and/or description.
    Use this tool to modify the details of an issue that already exists.
    You can update either the summary, description, or both.
    """
    issue_id: str = Field(description="ID or key of the issue to update (e.g., 'PROJ-123')")
    summary: str | None = Field(default=None, description="New summary text for the issue (leave as None to keep unchanged)")
    description: str | None = Field(default=None, description="New description text for the issue (leave as None to keep unchanged)")


def jira_update_issue_func(issue_id: str, summary: str | None, description: str | None, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        fields = {}
        if summary is not None:
            fields["summary"] = summary
        if description is not None:
            fields["description"] = description
        data = {"fields": fields}
        res = JiraService.update_issue(user, issue_id, data)
        return json.dumps(res)
    except Exception as e:
        return f"Error updating issue: {e}"


jira_update_issue_tool = AgentTool(params=JiraUpdateIssueParams, function=jira_update_issue_func, pass_context=True)


class JiraTransitionIssueParams(BaseModel):
    """
    Change the status of a Jira issue by applying a workflow transition.
    Use this tool to move issues between statuses (e.g., from "To Do" to "In Progress").
    You'll need both the issue ID and the specific transition ID to apply.
    """
    issue_id: str = Field(description="ID or key of the issue (e.g., 'PROJ-123')")
    transition_id: str = Field(description="ID of the transition to apply (use JiraSearchIssues first to find valid transition IDs)")


def jira_transition_issue_func(issue_id: str, transition_id: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.transition_issue(user, issue_id, transition_id)
        return json.dumps(res)
    except Exception as e:
        return f"Error transitioning issue: {e}"


jira_transition_issue_tool = AgentTool(params=JiraTransitionIssueParams, function=jira_transition_issue_func, pass_context=True)


class JiraAssignIssueParams(BaseModel):
    """
    Assign a Jira issue to a specific user.
    Use this tool when you need to allocate an issue to someone based on their account ID.
    This will make the specified user the assignee of the issue.
    """
    issue_id: str = Field(description="ID or key of the issue (e.g., 'PROJ-123')")
    account_id: str = Field(description="Account ID of the user to assign the issue to (e.g., '5b10a2844c20165700ede21g')")


def jira_assign_issue_func(issue_id: str, account_id: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.assign_issue(user, issue_id, account_id)
        return json.dumps(res)
    except Exception as e:
        return f"Error assigning issue: {e}"


jira_assign_issue_tool = AgentTool(params=JiraAssignIssueParams, function=jira_assign_issue_func, pass_context=True)


class JiraUnassignIssueParams(BaseModel):
    """
    Remove the current assignee from a Jira issue.
    Use this tool to clear the assignee field, making the issue unassigned.
    This is useful when reassigning work or when the original assignee is no longer responsible.
    """
    issue_id: str = Field(description="ID or key of the issue to unassign (e.g., 'PROJ-123')")


def jira_unassign_issue_func(issue_id: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.unassign_issue(user, issue_id)
        return json.dumps(res)
    except Exception as e:
        return f"Error unassigning issue: {e}"


jira_unassign_issue_tool = AgentTool(params=JiraUnassignIssueParams, function=jira_unassign_issue_func, pass_context=True)


class JiraGetSprintsParams(BaseModel):
    """
    Retrieve all sprints from a specified Jira board.
    Use this tool to get information about current, future, and past sprints in an Agile board.
    Results include sprint names, start dates, end dates, and states.
    """
    board_id: str = Field(description="ID of the Jira board (e.g., '123')")


def jira_get_sprints_func(board_id: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.list_sprints(user, board_id)
        return json.dumps(res)
    except Exception as e:
        return f"Error getting sprints: {e}"


jira_get_sprints_tool = AgentTool(params=JiraGetSprintsParams, function=jira_get_sprints_func, pass_context=True)


class JiraGetSprintIssuesParams(BaseModel):
    """
    Retrieve all issues currently assigned to a specific sprint.
    Use this tool to see what work is planned for or in progress in a particular sprint.
    Results include all issues regardless of their current status.
    """
    sprint_id: str = Field(description="ID of the sprint to retrieve issues from (e.g., '456')")


def jira_get_sprint_issues_func(sprint_id: str, context: dict) -> str:
    try:
        user = User.get_user(context["user_id"])
        res = JiraService.get_sprint_issues(user, sprint_id)
        return json.dumps(res)
    except Exception as e:
        return f"Error getting sprint issues: {e}"


jira_get_sprint_issues_tool = AgentTool(params=JiraGetSprintIssuesParams, function=jira_get_sprint_issues_func, pass_context=True)
