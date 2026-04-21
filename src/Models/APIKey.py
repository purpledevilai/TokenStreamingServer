import os
from datetime import datetime, timedelta
from typing import Optional
import uuid
from AWS.DynamoDB import get_item, put_item, delete_item
from pydantic import BaseModel
from lib.JWT import generate_jwt, validate_jwt, extract_jwt_contents

API_KEYS_TABLE_NAME = os.environ["API_KEYS_TABLE_NAME"]
API_KEYS_PRIMARY_KEY = os.environ["API_KEYS_PRIMARY_KEY"]
JWT_SECRET = os.environ["JWT_SECRET"]

class APIKey(BaseModel):
    api_key_id: str
    org_id: str
    token: str
    valid: bool
    type: str  # "org" or "client"
    user_id: str  # For org tokens: same as api_key_id, For client tokens: the creator's user_id
    client_id: Optional[str] = None  # Client tokens only: scopes the key to a specific org-owned client
    created_at: int
    updated_at: int
    expires_at: Optional[int] = None  # DynamoDB TTL; null means no automatic cleanup

def create_org_api_key(org_id: str) -> APIKey:
    """
    Create an org token with 100-year expiration.
    For org tokens, user_id is set to the api_key_id itself (self-referential).
    """
    api_key_id = str(uuid.uuid4())
    
    # Generate JWT with 100-year expiration
    token = generate_jwt(
        secret=JWT_SECRET,
        contents={
            "api_key_id": api_key_id,
            "org_id": org_id,
            "type": "org",
            "user_id": api_key_id  # Self-referential for org tokens
        },
        expires_in=timedelta(days=365 * 100)  # 100 years
    )
    
    created_at = int(datetime.now().timestamp())
    
    api_key = APIKey(
        api_key_id=api_key_id,
        org_id=org_id,
        token=token,
        valid=True,
        type="org",
        user_id=api_key_id,  # Self-referential
        created_at=created_at,
        updated_at=created_at
    )
    
    put_item(API_KEYS_TABLE_NAME, api_key.model_dump())
    return api_key

def create_client_api_key(
    org_id: str,
    user_id: str,
    client_id: Optional[str] = None,
    expires_in: timedelta = timedelta(minutes=2),
) -> APIKey:
    """
    Create a client token.

    - ``user_id`` is inherited from the creator (org token or cognito user).
    - ``client_id`` (optional) scopes the token to a specific org-owned client.
    - ``expires_in`` controls both the JWT exp claim and the DynamoDB ``expires_at`` TTL attr.
    """
    api_key_id = str(uuid.uuid4())

    jwt_contents = {
        "api_key_id": api_key_id,
        "org_id": org_id,
        "type": "client",
        "user_id": user_id,
    }
    if client_id is not None:
        jwt_contents["client_id"] = client_id

    token = generate_jwt(
        secret=JWT_SECRET,
        contents=jwt_contents,
        expires_in=expires_in,
    )

    created_at = int(datetime.now().timestamp())
    expires_at = int((datetime.now() + expires_in).timestamp())

    api_key = APIKey(
        api_key_id=api_key_id,
        org_id=org_id,
        token=token,
        valid=True,
        type="client",
        user_id=user_id,
        client_id=client_id,
        created_at=created_at,
        updated_at=created_at,
        expires_at=expires_at,
    )

    put_item(API_KEYS_TABLE_NAME, api_key.model_dump())
    return api_key

def validate_api_key(token: str) -> bool:
    """
    Validate an API key token.
    Returns True if the token is valid JWT and the key exists in DB with valid=True.
    """
    # First validate JWT signature and expiration
    if not validate_jwt(JWT_SECRET, token):
        return False
    
    try:
        # Extract contents to get api_key_id
        contents = extract_jwt_contents(JWT_SECRET, token)
        api_key_id = contents.get("api_key_id")
        
        if not api_key_id:
            return False
        
        # Check if the key exists and is valid
        item = get_item(API_KEYS_TABLE_NAME, API_KEYS_PRIMARY_KEY, api_key_id)
        if not item:
            return False
        
        api_key = APIKey(**item)
        return api_key.valid
        
    except Exception:
        return False

def get_api_key_contents(token: str) -> dict:
    """
    Extract and return the contents of a valid API key token.
    Raises an exception if the token is invalid.
    """
    if not validate_api_key(token):
        raise Exception("Invalid API key token", 401)
    
    return extract_jwt_contents(JWT_SECRET, token)

def get_api_key(api_key_id: str) -> APIKey:
    """
    Get an API key by its ID.
    """
    item = get_item(API_KEYS_TABLE_NAME, API_KEYS_PRIMARY_KEY, api_key_id)
    if item is None:
        raise Exception(f"APIKey with id: {api_key_id} does not exist", 404)
    return APIKey(**item)

def revoke_api_key(api_key_id: str) -> APIKey:
    """
    Revoke an API key by setting valid=False.
    """
    api_key = get_api_key(api_key_id)
    api_key.valid = False
    api_key.updated_at = int(datetime.now().timestamp())
    put_item(API_KEYS_TABLE_NAME, api_key.model_dump())
    return api_key

def delete_api_key(api_key_id: str) -> None:
    """
    Permanently delete an API key from the database.
    """
    delete_item(API_KEYS_TABLE_NAME, API_KEYS_PRIMARY_KEY, api_key_id)

def get_api_key_type(token: str) -> str:
    """
    Extract the type from a valid API key token.
    Returns "client" as default for safety.
    """
    try:
        contents = get_api_key_contents(token)
        return contents.get("type", "client")
    except Exception:
        return "client"

