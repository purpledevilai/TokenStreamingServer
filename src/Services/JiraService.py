import os
import time
import requests
from AWS.CloudWatchLogs import get_logger
from Models import Integration, User

logger = get_logger(log_level=os.environ.get("LOG_LEVEL", "INFO"))

JIRA_TOKEN_URL = "https://auth.atlassian.com/oauth/token"
ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"


def _get_jira_integration(user: User.User) -> Integration.Integration:
    if len(user.organizations) == 0:
        raise Exception("User is not a member of any organizations", 400)
    org_id = user.organizations[0]
    integrations = Integration.get_integrations_in_org(org_id)
    for integration in integrations:
        if integration.type == "jira":
            return integration
    raise Exception("Jira integration not found", 404)


def _refresh_token(integration: Integration.Integration) -> Integration.Integration:
    refresh_token = integration.integration_config.get("refresh_token")
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["JIRA_CLIENT_ID"],
        "client_secret": os.environ["JIRA_CLIENT_SECRET"],
        "refresh_token": refresh_token,
    }
    resp = requests.post(JIRA_TOKEN_URL, json=payload)
    if resp.status_code != 200:
        raise Exception("Failed to refresh Jira token", resp.status_code)
    data = resp.json()
    integration.integration_config.update(
        {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "expires_in": data.get("expires_in"),
            "scope": data.get("scope"),
            "expires_at": int(time.time()) + data.get("expires_in", 0),
        }
    )
    Integration.save_integration(integration)
    return integration


def _ensure_token(integration: Integration.Integration) -> str:
    expires_at = integration.integration_config.get("expires_at")
    if expires_at and expires_at <= int(time.time()):
        integration = _refresh_token(integration)
    return integration.integration_config.get("access_token")


def jira_api_request(user: User.User, method: str, path: str, **kwargs):
    integration = _get_jira_integration(user)
    access_token = _ensure_token(integration)
    cloud_id = integration.integration_config.get("cloud_id")
    if not cloud_id:
        raise Exception("No Jira cloud id stored", 400)
    url = f"https://api.atlassian.com/ex/jira/{cloud_id}{path}"
    headers = kwargs.pop("headers", {})
    headers.update({"Authorization": f"Bearer {access_token}", "Accept": "application/json"})
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        raise Exception(f"Jira API error: {resp.text}", resp.status_code)
    if resp.text:
        return resp.json()
    return {}


def list_projects(user: User.User):
    return jira_api_request(user, "GET", "/rest/api/3/project/search")


def create_issue(user: User.User, data: dict):
    return jira_api_request(user, "POST", "/rest/api/3/issue", json=data)


def search_issues(user: User.User, jql: str | None = None):
    params = {"jql": jql} if jql else {}
    return jira_api_request(user, "GET", "/rest/api/3/search", params=params)


def update_issue(user: User.User, issue_id: str, data: dict):
    return jira_api_request(user, "PUT", f"/rest/api/3/issue/{issue_id}", json=data)


def transition_issue(user: User.User, issue_id: str, transition_id: str):
    data = {"transition": {"id": transition_id}}
    return jira_api_request(
        user,
        "POST",
        f"/rest/api/3/issue/{issue_id}/transitions",
        json=data,
    )


def assign_issue(user: User.User, issue_id: str, account_id: str):
    data = {"accountId": account_id}
    return jira_api_request(user, "PUT", f"/rest/api/3/issue/{issue_id}/assignee", json=data)


def unassign_issue(user: User.User, issue_id: str):
    return jira_api_request(user, "DELETE", f"/rest/api/3/issue/{issue_id}/assignee")


def list_sprints(user: User.User, board_id: str):
    return jira_api_request(user, "GET", f"/rest/agile/1.0/board/{board_id}/sprint")


def get_sprint_issues(user: User.User, sprint_id: str):
    return jira_api_request(user, "GET", f"/rest/agile/1.0/sprint/{sprint_id}/issue")
