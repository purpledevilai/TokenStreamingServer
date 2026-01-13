import os
import time
import requests
from AWS.CloudWatchLogs import get_logger
from Models import Integration

logger = get_logger(log_level=os.environ.get("LOG_LEVEL", "INFO"))

OUTLOOK_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

# Scopes needed for token refresh
OUTLOOK_SCOPES = [
    "https://graph.microsoft.com/Mail.ReadWrite",
    "https://graph.microsoft.com/Mail.Send",
    "https://graph.microsoft.com/User.Read",
    "offline_access",
]


def _get_outlook_integration_by_id(integration_id: str) -> Integration.Integration:
    """Get an Outlook integration by its ID."""
    integration = Integration.get_integration(integration_id)
    if integration.type != "outlook":
        raise Exception(f"Integration {integration_id} is not an Outlook integration", 400)
    return integration


def _refresh_token(integration: Integration.Integration) -> Integration.Integration:
    """Refresh the access token using the refresh token."""
    refresh_token = integration.integration_config.get("refresh_token")
    if not refresh_token:
        raise Exception("No refresh token available", 400)
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["OUTLOOK_CLIENT_ID"],
        "client_secret": os.environ["OUTLOOK_CLIENT_SECRET"],
        "refresh_token": refresh_token,
        "scope": " ".join(OUTLOOK_SCOPES),
    }
    resp = requests.post(OUTLOOK_TOKEN_URL, data=payload)
    if resp.status_code != 200:
        logger.error(f"Failed to refresh Outlook token: {resp.text}")
        raise Exception("Failed to refresh Outlook token", resp.status_code)
    
    data = resp.json()
    integration.integration_config.update({
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in"),
        "scope": data.get("scope"),
        "expires_at": int(time.time()) + data.get("expires_in", 0),
    })
    # Microsoft may return a new refresh_token
    if "refresh_token" in data:
        integration.integration_config["refresh_token"] = data["refresh_token"]
    
    Integration.save_integration(integration)
    return integration


def _ensure_token(integration: Integration.Integration) -> str:
    """Ensure the access token is valid, refreshing if necessary."""
    expires_at = integration.integration_config.get("expires_at")
    # Refresh if token expires in less than 60 seconds
    if expires_at and expires_at <= int(time.time()) + 60:
        integration = _refresh_token(integration)
    return integration.integration_config.get("access_token")


def outlook_api_request(integration_id: str, method: str, path: str, **kwargs):
    """Make an authenticated request to the Microsoft Graph API."""
    integration = _get_outlook_integration_by_id(integration_id)
    access_token = _ensure_token(integration)
    
    url = f"{GRAPH_API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    })
    
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        logger.error(f"Outlook API error: {resp.text}")
        raise Exception(f"Outlook API error: {resp.text}", resp.status_code)
    
    if resp.text:
        return resp.json()
    return {}


# ==================== Message Functions ====================

def list_messages(integration_id: str, folder_id: str = None, filter_query: str = None, 
                  search_query: str = None, max_results: int = 10, select: list = None):
    """
    List messages in a mail folder or all messages.
    
    Args:
        integration_id: The Outlook integration ID
        folder_id: Optional folder ID to filter by (e.g., 'inbox', 'drafts', 'sentitems')
        filter_query: OData $filter query (e.g., "isRead eq false")
        search_query: OData $search query for full-text search
        max_results: Maximum number of messages to return (default 10)
        select: List of fields to select
    
    Returns:
        List of message metadata
    """
    if folder_id:
        path = f"/me/mailFolders/{folder_id}/messages"
    else:
        path = "/me/messages"
    
    params = {"$top": max_results}
    
    if filter_query:
        params["$filter"] = filter_query
    if search_query:
        params["$search"] = f'"{search_query}"'
    if select:
        params["$select"] = ",".join(select)
    
    # Default ordering by received date descending
    params["$orderby"] = "receivedDateTime desc"
    
    return outlook_api_request(integration_id, "GET", path, params=params)


def get_message(integration_id: str, message_id: str, select: list = None):
    """
    Get a specific message by ID.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        select: Optional list of fields to select
    
    Returns:
        Full message data
    """
    path = f"/me/messages/{message_id}"
    params = {}
    if select:
        params["$select"] = ",".join(select)
    
    return outlook_api_request(integration_id, "GET", path, params=params if params else None)


def send_message(integration_id: str, to: str, subject: str, body: str, html: bool = False):
    """
    Send an email.
    
    Args:
        integration_id: The Outlook integration ID
        to: Recipient email address
        subject: Email subject
        body: Email body content
        html: If True, body is treated as HTML
    
    Returns:
        Empty response on success (202 Accepted)
    """
    message_body = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "HTML" if html else "Text",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to
                    }
                }
            ]
        }
    }
    
    return outlook_api_request(integration_id, "POST", "/me/sendMail", json=message_body)


def update_message(integration_id: str, message_id: str, updates: dict):
    """
    Update a message's properties.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        updates: Dict of properties to update (e.g., {"isRead": True})
    
    Returns:
        Updated message metadata
    """
    return outlook_api_request(integration_id, "PATCH", f"/me/messages/{message_id}", json=updates)


def delete_message(integration_id: str, message_id: str):
    """
    Permanently delete a message.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID to permanently delete
    
    Returns:
        Empty dict on success
    """
    return outlook_api_request(integration_id, "DELETE", f"/me/messages/{message_id}")


def move_message(integration_id: str, message_id: str, destination_folder_id: str):
    """
    Move a message to a different folder.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        destination_folder_id: The destination folder ID (e.g., 'inbox', 'deleteditems', 'archive')
    
    Returns:
        Moved message metadata
    """
    return outlook_api_request(
        integration_id,
        "POST",
        f"/me/messages/{message_id}/move",
        json={"destinationId": destination_folder_id}
    )


# ==================== Draft Functions ====================

def create_draft(integration_id: str, to: str = None, subject: str = None, body: str = None, html: bool = False):
    """
    Create a draft email.
    
    Args:
        integration_id: The Outlook integration ID
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body content (optional)
        html: If True, body is treated as HTML
    
    Returns:
        Created draft metadata
    """
    message = {}
    
    if subject:
        message["subject"] = subject
    if body:
        message["body"] = {
            "contentType": "HTML" if html else "Text",
            "content": body
        }
    if to:
        message["toRecipients"] = [
            {
                "emailAddress": {
                    "address": to
                }
            }
        ]
    
    return outlook_api_request(integration_id, "POST", "/me/messages", json=message)


def list_drafts(integration_id: str, max_results: int = 10):
    """
    List drafts in the user's mailbox.
    
    Args:
        integration_id: The Outlook integration ID
        max_results: Maximum number of drafts to return (default 10)
    
    Returns:
        List of draft metadata
    """
    return list_messages(integration_id, folder_id="drafts", max_results=max_results)


def get_draft(integration_id: str, draft_id: str):
    """
    Get a specific draft by ID.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft (message) ID
    
    Returns:
        Full draft data
    """
    return get_message(integration_id, draft_id)


def update_draft(integration_id: str, draft_id: str, to: str = None, subject: str = None, 
                 body: str = None, html: bool = False):
    """
    Update an existing draft.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft ID to update
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body content (optional)
        html: If True, body is treated as HTML
    
    Returns:
        Updated draft metadata
    """
    updates = {}
    
    if subject is not None:
        updates["subject"] = subject
    if body is not None:
        updates["body"] = {
            "contentType": "HTML" if html else "Text",
            "content": body
        }
    if to is not None:
        updates["toRecipients"] = [
            {
                "emailAddress": {
                    "address": to
                }
            }
        ]
    
    return update_message(integration_id, draft_id, updates)


def send_draft(integration_id: str, draft_id: str):
    """
    Send an existing draft. This removes the draft from the drafts folder.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft ID to send
    
    Returns:
        Empty dict on success
    """
    return outlook_api_request(integration_id, "POST", f"/me/messages/{draft_id}/send")


def delete_draft(integration_id: str, draft_id: str):
    """
    Delete a draft permanently.
    
    Args:
        integration_id: The Outlook integration ID
        draft_id: The draft ID to delete
    
    Returns:
        Empty dict on success
    """
    return delete_message(integration_id, draft_id)


# ==================== Folder Functions ====================

def list_folders(integration_id: str, include_hidden: bool = False):
    """
    Get all mail folders for the user's mailbox.
    
    Args:
        integration_id: The Outlook integration ID
        include_hidden: Whether to include hidden folders
    
    Returns:
        List of folder data
    """
    params = {}
    if not include_hidden:
        params["$filter"] = "isHidden eq false"
    
    return outlook_api_request(integration_id, "GET", "/me/mailFolders", params=params if params else None)


def get_folder(integration_id: str, folder_id: str):
    """
    Get a specific folder by ID.
    
    Args:
        integration_id: The Outlook integration ID
        folder_id: The folder ID (can be well-known names like 'inbox', 'drafts', etc.)
    
    Returns:
        Folder data
    """
    return outlook_api_request(integration_id, "GET", f"/me/mailFolders/{folder_id}")


def create_folder(integration_id: str, display_name: str, parent_folder_id: str = None):
    """
    Create a new mail folder.
    
    Args:
        integration_id: The Outlook integration ID
        display_name: The display name for the new folder
        parent_folder_id: Optional parent folder ID (creates subfolder if provided)
    
    Returns:
        Created folder data
    """
    body = {"displayName": display_name}
    
    if parent_folder_id:
        path = f"/me/mailFolders/{parent_folder_id}/childFolders"
    else:
        path = "/me/mailFolders"
    
    return outlook_api_request(integration_id, "POST", path, json=body)


def delete_folder(integration_id: str, folder_id: str):
    """
    Delete a mail folder. Built-in folders cannot be deleted.
    
    Args:
        integration_id: The Outlook integration ID
        folder_id: The folder ID to delete
    
    Returns:
        Empty dict on success
    """
    return outlook_api_request(integration_id, "DELETE", f"/me/mailFolders/{folder_id}")


# ==================== Category Functions ====================

def get_categories(integration_id: str):
    """
    Get all available categories (similar to Gmail labels).
    
    Args:
        integration_id: The Outlook integration ID
    
    Returns:
        List of category data
    """
    return outlook_api_request(integration_id, "GET", "/me/outlook/masterCategories")


def update_message_categories(integration_id: str, message_id: str, categories: list):
    """
    Update categories on a message.
    
    Args:
        integration_id: The Outlook integration ID
        message_id: The message ID
        categories: List of category names to set on the message
    
    Returns:
        Updated message metadata
    """
    return update_message(integration_id, message_id, {"categories": categories})


# ==================== Helper Functions ====================

def parse_message_to_summary(message: dict) -> dict:
    """
    Parse a message into a summary format.
    
    Args:
        message: Raw message from Graph API
    
    Returns:
        Summarized message dict
    """
    from_addr = message.get("from", {}).get("emailAddress", {})
    to_recipients = message.get("toRecipients", [])
    to_addr = to_recipients[0].get("emailAddress", {}) if to_recipients else {}
    
    return {
        "id": message.get("id"),
        "conversation_id": message.get("conversationId"),
        "from": from_addr.get("address", ""),
        "from_name": from_addr.get("name", ""),
        "to": to_addr.get("address", ""),
        "subject": message.get("subject", "(No Subject)"),
        "received_date": message.get("receivedDateTime", ""),
        "snippet": message.get("bodyPreview", ""),
        "is_read": message.get("isRead", False),
        "is_draft": message.get("isDraft", False),
        "has_attachments": message.get("hasAttachments", False),
        "importance": message.get("importance", "normal"),
        "categories": message.get("categories", []),
        "flag": message.get("flag", {}).get("flagStatus", "notFlagged"),
    }


def parse_message_body(message: dict) -> str:
    """
    Extract the body text from a message.
    
    Args:
        message: Raw message from Graph API
    
    Returns:
        The message body as text
    """
    body = message.get("body", {})
    return body.get("content", "")


def get_well_known_folder_id(folder_name: str) -> str:
    """
    Get the well-known folder name for common folders.
    
    Outlook supports these well-known folder names:
    - inbox, drafts, sentitems, deleteditems, junkemail, archive, 
    - clutter, outbox, recoverableitemsdeletions
    
    Args:
        folder_name: Common folder name
    
    Returns:
        Well-known folder ID string
    """
    folder_map = {
        "inbox": "inbox",
        "drafts": "drafts",
        "sent": "sentitems",
        "sentitems": "sentitems",
        "trash": "deleteditems",
        "deleted": "deleteditems",
        "deleteditems": "deleteditems",
        "junk": "junkemail",
        "spam": "junkemail",
        "junkemail": "junkemail",
        "archive": "archive",
        "outbox": "outbox",
    }
    return folder_map.get(folder_name.lower(), folder_name)

