import os
import time
import base64
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from AWS.CloudWatchLogs import get_logger
from Models import Integration

logger = get_logger(log_level=os.environ.get("LOG_LEVEL", "INFO"))

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def _get_gmail_integration_by_id(integration_id: str) -> Integration.Integration:
    """Get a Gmail integration by its ID."""
    integration = Integration.get_integration(integration_id)
    if integration.type != "gmail":
        raise Exception(f"Integration {integration_id} is not a Gmail integration", 400)
    return integration


def _refresh_token(integration: Integration.Integration) -> Integration.Integration:
    """Refresh the access token using the refresh token."""
    refresh_token = integration.integration_config.get("refresh_token")
    if not refresh_token:
        raise Exception("No refresh token available", 400)
    
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": refresh_token,
    }
    resp = requests.post(GMAIL_TOKEN_URL, data=payload)
    if resp.status_code != 200:
        logger.error(f"Failed to refresh Gmail token: {resp.text}")
        raise Exception("Failed to refresh Gmail token", resp.status_code)
    
    data = resp.json()
    integration.integration_config.update({
        "access_token": data["access_token"],
        "expires_in": data.get("expires_in"),
        "scope": data.get("scope"),
        "expires_at": int(time.time()) + data.get("expires_in", 0),
    })
    # Note: Google doesn't always return a new refresh_token
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


def gmail_api_request(integration_id: str, method: str, path: str, **kwargs):
    """Make an authenticated request to the Gmail API."""
    integration = _get_gmail_integration_by_id(integration_id)
    access_token = _ensure_token(integration)
    
    url = f"{GMAIL_API_BASE}{path}"
    headers = kwargs.pop("headers", {})
    headers.update({
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    })
    
    resp = requests.request(method, url, headers=headers, **kwargs)
    if resp.status_code >= 400:
        logger.error(f"Gmail API error: {resp.text}")
        raise Exception(f"Gmail API error: {resp.text}", resp.status_code)
    
    if resp.text:
        return resp.json()
    return {}


# ==================== Gmail API Functions ====================

def list_messages(integration_id: str, query: str = None, max_results: int = 10, label_ids: list = None):
    """
    List messages in the user's mailbox.
    
    Args:
        integration_id: The Gmail integration ID
        query: Gmail search query (e.g., "is:unread", "from:example@gmail.com")
        max_results: Maximum number of messages to return (default 10)
        label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
    
    Returns:
        List of message metadata
    """
    params = {"maxResults": max_results}
    if query:
        params["q"] = query
    if label_ids:
        params["labelIds"] = label_ids
    
    return gmail_api_request(integration_id, "GET", "/users/me/messages", params=params)


def get_message(integration_id: str, message_id: str, format: str = "full"):
    """
    Get a specific message by ID.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        format: The format to return (minimal, full, raw, metadata)
    
    Returns:
        Full message data
    """
    params = {"format": format}
    return gmail_api_request(integration_id, "GET", f"/users/me/messages/{message_id}", params=params)


def send_message(integration_id: str, to: str, subject: str, body: str, html: bool = False):
    """
    Send an email.
    
    Args:
        integration_id: The Gmail integration ID
        to: Recipient email address
        subject: Email subject
        body: Email body content
        html: If True, body is treated as HTML
    
    Returns:
        Sent message metadata
    """
    if html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body, "html"))
    else:
        message = MIMEText(body)
    
    message["to"] = to
    message["subject"] = subject
    
    # Encode the message
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    
    return gmail_api_request(
        integration_id, 
        "POST", 
        "/users/me/messages/send",
        json={"raw": raw}
    )


def modify_message(integration_id: str, message_id: str, add_labels: list = None, remove_labels: list = None):
    """
    Modify labels on a message.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID
        add_labels: Labels to add (e.g., ["UNREAD"])
        remove_labels: Labels to remove (e.g., ["UNREAD"])
    
    Returns:
        Modified message metadata
    """
    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    
    return gmail_api_request(
        integration_id,
        "POST",
        f"/users/me/messages/{message_id}/modify",
        json=body
    )


def mark_as_read(integration_id: str, message_id: str):
    """Mark a message as read by removing the UNREAD label."""
    return modify_message(integration_id, message_id, remove_labels=["UNREAD"])


def mark_as_unread(integration_id: str, message_id: str):
    """Mark a message as unread by adding the UNREAD label."""
    return modify_message(integration_id, message_id, add_labels=["UNREAD"])


def get_labels(integration_id: str):
    """Get all labels for the user's mailbox."""
    return gmail_api_request(integration_id, "GET", "/users/me/labels")


def parse_message_headers(message: dict) -> dict:
    """
    Parse useful headers from a message.
    
    Returns:
        Dict with from, to, subject, date
    """
    headers = message.get("payload", {}).get("headers", [])
    result = {}
    for header in headers:
        name = header.get("name", "").lower()
        if name in ["from", "to", "subject", "date"]:
            result[name] = header.get("value")
    return result


def parse_message_body(message: dict) -> str:
    """
    Extract the body text from a message.
    
    Returns:
        The message body as plain text
    """
    payload = message.get("payload", {})
    
    # Simple message with body directly in payload
    if "body" in payload and payload["body"].get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    
    # Multipart message - look for text/plain or text/html
    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    
    # Fallback to HTML if no plain text
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    
    # Check nested parts (for complex multipart messages)
    for part in parts:
        nested_parts = part.get("parts", [])
        for nested in nested_parts:
            mime_type = nested.get("mimeType", "")
            if mime_type == "text/plain" and nested.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(nested["body"]["data"]).decode("utf-8")
    
    return ""


# ==================== Draft Functions ====================

def _create_mime_message(to: str = None, subject: str = None, body: str = None, html: bool = False) -> str:
    """
    Create a MIME message and return it as a base64url encoded string.
    
    Args:
        to: Recipient email address (optional for drafts)
        subject: Email subject
        body: Email body content
        html: If True, body is treated as HTML
    
    Returns:
        Base64url encoded message string
    """
    if html:
        message = MIMEMultipart("alternative")
        message.attach(MIMEText(body or "", "html"))
    else:
        message = MIMEText(body or "")
    
    if to:
        message["to"] = to
    if subject:
        message["subject"] = subject
    
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")


def create_draft(integration_id: str, to: str = None, subject: str = None, body: str = None, html: bool = False):
    """
    Create a draft email.
    
    Args:
        integration_id: The Gmail integration ID
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body content (optional)
        html: If True, body is treated as HTML
    
    Returns:
        Created draft metadata
    """
    raw = _create_mime_message(to, subject, body, html)
    
    return gmail_api_request(
        integration_id,
        "POST",
        "/users/me/drafts",
        json={"message": {"raw": raw}}
    )


def list_drafts(integration_id: str, max_results: int = 10):
    """
    List drafts in the user's mailbox.
    
    Args:
        integration_id: The Gmail integration ID
        max_results: Maximum number of drafts to return (default 10)
    
    Returns:
        List of draft metadata
    """
    params = {"maxResults": max_results}
    return gmail_api_request(integration_id, "GET", "/users/me/drafts", params=params)


def get_draft(integration_id: str, draft_id: str, format: str = "full"):
    """
    Get a specific draft by ID.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID
        format: The format to return (minimal, full, raw, metadata)
    
    Returns:
        Full draft data including the message
    """
    params = {"format": format}
    return gmail_api_request(integration_id, "GET", f"/users/me/drafts/{draft_id}", params=params)


def update_draft(integration_id: str, draft_id: str, to: str = None, subject: str = None, body: str = None, html: bool = False):
    """
    Update an existing draft.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID to update
        to: Recipient email address (optional)
        subject: Email subject (optional)
        body: Email body content (optional)
        html: If True, body is treated as HTML
    
    Returns:
        Updated draft metadata
    """
    raw = _create_mime_message(to, subject, body, html)
    
    return gmail_api_request(
        integration_id,
        "PUT",
        f"/users/me/drafts/{draft_id}",
        json={"message": {"raw": raw}}
    )


def send_draft(integration_id: str, draft_id: str):
    """
    Send an existing draft. This removes the draft from the drafts folder.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID to send
    
    Returns:
        Sent message metadata
    """
    return gmail_api_request(
        integration_id,
        "POST",
        "/users/me/drafts/send",
        json={"id": draft_id}
    )


def delete_draft(integration_id: str, draft_id: str):
    """
    Delete a draft permanently.
    
    Args:
        integration_id: The Gmail integration ID
        draft_id: The draft ID to delete
    
    Returns:
        Empty dict on success
    """
    return gmail_api_request(integration_id, "DELETE", f"/users/me/drafts/{draft_id}")


# ==================== Label Functions ====================

def get_label(integration_id: str, label_id: str):
    """
    Get a specific label by ID.
    
    Args:
        integration_id: The Gmail integration ID
        label_id: The label ID
    
    Returns:
        Label data
    """
    return gmail_api_request(integration_id, "GET", f"/users/me/labels/{label_id}")


def create_label(integration_id: str, name: str, label_list_visibility: str = "labelShow", message_list_visibility: str = "show"):
    """
    Create a new label.
    
    Args:
        integration_id: The Gmail integration ID
        name: The display name of the label
        label_list_visibility: Visibility in the label list (labelShow, labelShowIfUnread, labelHide)
        message_list_visibility: Visibility in the message list (show, hide)
    
    Returns:
        Created label data
    """
    body = {
        "name": name,
        "labelListVisibility": label_list_visibility,
        "messageListVisibility": message_list_visibility,
    }
    return gmail_api_request(integration_id, "POST", "/users/me/labels", json=body)


def delete_label(integration_id: str, label_id: str):
    """
    Delete a label. System labels cannot be deleted.
    
    Args:
        integration_id: The Gmail integration ID
        label_id: The label ID to delete
    
    Returns:
        Empty dict on success
    """
    return gmail_api_request(integration_id, "DELETE", f"/users/me/labels/{label_id}")


def update_label(integration_id: str, label_id: str, name: str = None, label_list_visibility: str = None, message_list_visibility: str = None):
    """
    Update a label's properties.
    
    Args:
        integration_id: The Gmail integration ID
        label_id: The label ID to update
        name: New display name (optional)
        label_list_visibility: New visibility in label list (optional)
        message_list_visibility: New visibility in message list (optional)
    
    Returns:
        Updated label data
    """
    body = {}
    if name:
        body["name"] = name
    if label_list_visibility:
        body["labelListVisibility"] = label_list_visibility
    if message_list_visibility:
        body["messageListVisibility"] = message_list_visibility
    
    return gmail_api_request(integration_id, "PATCH", f"/users/me/labels/{label_id}", json=body)


# ==================== Email Lifecycle Functions ====================

def trash_message(integration_id: str, message_id: str):
    """
    Move a message to the trash.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to trash
    
    Returns:
        Trashed message metadata
    """
    return gmail_api_request(integration_id, "POST", f"/users/me/messages/{message_id}/trash")


def untrash_message(integration_id: str, message_id: str):
    """
    Remove a message from the trash.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to restore
    
    Returns:
        Restored message metadata
    """
    return gmail_api_request(integration_id, "POST", f"/users/me/messages/{message_id}/untrash")


def delete_message(integration_id: str, message_id: str):
    """
    Permanently delete a message. This action is irreversible.
    
    Args:
        integration_id: The Gmail integration ID
        message_id: The message ID to permanently delete
    
    Returns:
        Empty dict on success
    """
    return gmail_api_request(integration_id, "DELETE", f"/users/me/messages/{message_id}")

