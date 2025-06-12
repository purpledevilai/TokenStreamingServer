import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel
from AWS.DynamoDB import (
    get_item,
    get_items_by_scan,
    get_all_items_by_index,
    put_item,
    delete_item,
)
from AWS.CloudWatchLogs import get_logger
from Models import User

logger = get_logger(log_level=os.environ["LOG_LEVEL"])

INTEGRATIONS_TABLE_NAME = os.environ["INTEGRATIONS_TABLE_NAME"]
INTEGRATIONS_PRIMARY_KEY = os.environ["INTEGRATIONS_PRIMARY_KEY"]


class Integration(BaseModel):
    integration_id: str
    org_id: str
    type: str
    integration_config: Dict[str, Any]
    created_at: int
    updated_at: int


class CreateIntegrationParams(BaseModel):
    type: str
    integration_config: Dict[str, Any]
    org_id: Optional[str] = None


class UpdateIntegrationParams(BaseModel):
    type: Optional[str] = None
    integration_config: Optional[Dict[str, Any]] = None


def integration_exists(integration_id: str) -> bool:
    return (
        get_item(INTEGRATIONS_TABLE_NAME, INTEGRATIONS_PRIMARY_KEY, integration_id) is not None
    )


def create_integration(
    org_id: str,
    type: str,
    integration_config: Dict[str, Any],
) -> Integration:
    now = int(datetime.timestamp(datetime.now()))
    data = {
        INTEGRATIONS_PRIMARY_KEY: str(uuid.uuid4()),
        "org_id": org_id,
        "type": type,
        "integration_config": integration_config,
        "created_at": now,
        "updated_at": now,
    }
    integration = Integration(**data)
    put_item(INTEGRATIONS_TABLE_NAME, data)
    return integration


def get_integration(integration_id: str) -> Integration:
    item = get_item(INTEGRATIONS_TABLE_NAME, INTEGRATIONS_PRIMARY_KEY, integration_id)
    if item is None:
        raise Exception(f"Integration with id: {integration_id} does not exist", 404)
    return Integration(**item)


def get_integration_for_user(integration_id: str, user: User.User) -> Integration:
    integration = get_integration(integration_id)
    if integration.org_id not in user.organizations:
        raise Exception("Integration does not belong to user's orgs", 403)
    return integration


def save_integration(integration: Integration) -> Integration:
    integration.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(INTEGRATIONS_TABLE_NAME, integration.model_dump())
    return integration


def delete_integration(integration_id: str) -> None:
    delete_item(INTEGRATIONS_TABLE_NAME, INTEGRATIONS_PRIMARY_KEY, integration_id)


def parse_integration_items(items: list[dict]) -> list[Integration]:
    integrations = []
    for item in items:
        try:
            integrations.append(Integration(**item))
        except Exception as e:
            logger.error(f"Error parsing integration: {e}")
    return integrations


def get_integrations_from_ids(integration_ids: list[str]) -> list[Integration]:
    items = get_items_by_scan(INTEGRATIONS_TABLE_NAME, INTEGRATIONS_PRIMARY_KEY, integration_ids)
    return parse_integration_items(items)


def get_integrations_in_org(org_id: str) -> list[Integration]:
    items = get_all_items_by_index(INTEGRATIONS_TABLE_NAME, "org_id", org_id)
    return parse_integration_items(items)


def delete_integrations_in_org(org_id: str) -> None:
    integrations = get_integrations_in_org(org_id)
    for integration in integrations:
        delete_integration(integration.integration_id)
