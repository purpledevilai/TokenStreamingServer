import os
from datetime import datetime
from AWS.DynamoDB import get_item, put_item, delete_item
from pydantic import BaseModel
from Models import APIKey

USERS_TABLE_NAME = os.environ["USERS_TABLE_NAME"]
USERS_PRIMARY_KEY = os.environ["USERS_PRIMARY_KEY"]

class User(BaseModel):
    user_id: str
    organizations: list[str]
    created_at: int
    updated_at: int

def user_exists(user_id: str) -> bool:
    return get_item(USERS_TABLE_NAME, USERS_PRIMARY_KEY, user_id) != None

def create_user(user_id: str) -> User:
    userData = {
        USERS_PRIMARY_KEY: user_id,
        "organizations": [],
        "created_at": int(datetime.timestamp(datetime.now())),
        "updated_at": int(datetime.timestamp(datetime.now())),
    }
    user = User(**userData)
    put_item(USERS_TABLE_NAME, userData)
    return user

def get_user(user_id: str) -> User:
    # Try to get from Users table first
    item = get_item(USERS_TABLE_NAME, USERS_PRIMARY_KEY, user_id)
    if item is not None:
        return User(**item)
    
    # If not found, try API Keys table (for API key authentication)
    try:
        api_key = APIKey.get_api_key(user_id)
        
        # Only return mocked user if API key is valid
        if api_key.valid:
            # Create a mocked User with the API key's details
            return User(
                user_id=api_key.user_id,  # Use the user_id from the API key
                organizations=[api_key.org_id],
                created_at=api_key.created_at,
                updated_at=api_key.updated_at
            )
    except Exception:
        pass  # API key not found, proceed to raise user not found error
    
    raise Exception(f"User with id: {user_id} does not exist")

def save_user(user: User) -> None:
    user.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(USERS_TABLE_NAME, user.model_dump())

def delete_user(user_id: str) -> None:
    delete_item(USERS_TABLE_NAME, USERS_PRIMARY_KEY, user_id)

def associate_organization_with_user(user_id: str, organization_id: str,) -> User:
    user = get_user(user_id)
    user.organizations.append(organization_id)
    save_user(user)
    return user

def user_is_member_of_organization(user_id: str, organization_id: str) -> bool:
    user = get_user(user_id)
    return organization_id in user.organizations
