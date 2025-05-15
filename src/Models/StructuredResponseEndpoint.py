import os
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from AWS.DynamoDB import get_item, put_item, delete_item, get_all_items_by_index
from Models import User

SRE_TABLE_NAME = os.environ["SRE_TABLE_NAME"]
SRE_PRIMARY_KEY = os.environ["SRE_PRIMARY_KEY"]


class StructuredResponseEndpoint(BaseModel):
    sre_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    pd_id: str
    is_public: bool
    created_at: int
    updated_at: int


class CreateSREParams(BaseModel):
    org_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    pd_id: str
    is_public: bool = False


class UpdateSREParams(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    pd_id: Optional[str] = None
    is_public: Optional[bool] = None


def sre_exists(sre_id: str) -> bool:
    return get_item(SRE_TABLE_NAME, SRE_PRIMARY_KEY, sre_id) is not None


def create_sre(org_id: str, name: str, description: Optional[str], pd_id: str, is_public: bool = False) -> StructuredResponseEndpoint:
    sre_id = str(uuid.uuid4())
    created_at = int(datetime.now().timestamp())
    updated_at = created_at
    sre = StructuredResponseEndpoint(
        sre_id=sre_id,
        org_id=org_id,
        name=name,
        description=description,
        pd_id=pd_id,
        is_public=is_public,
        created_at=created_at,
        updated_at=updated_at
    )
    put_item(SRE_TABLE_NAME, sre.model_dump())
    return sre


def get_sre(sre_id: str) -> StructuredResponseEndpoint:
    item = get_item(SRE_TABLE_NAME, SRE_PRIMARY_KEY, sre_id)
    if item is None:
        raise Exception(f"SRE {sre_id} not found", 404)
    return StructuredResponseEndpoint(**item)


def get_public_sre(sre_id: str) -> StructuredResponseEndpoint:
    sre = get_sre(sre_id)
    if not sre.is_public:
        raise Exception(f"SRE {sre_id} is not public", 403)
    return sre


def get_sre_for_org(sre_id: str, org_id: str) -> StructuredResponseEndpoint:
    sre = get_sre(sre_id)
    if sre.org_id != org_id:
        raise Exception(f"SRE {sre_id} not found for org", 404)
    return sre


def get_sre_for_user(sre_id: str, user: User.User) -> StructuredResponseEndpoint:
    sre = get_sre(sre_id)
    if sre.is_public:
        return sre
    if sre.org_id not in user.organizations:
        raise Exception(f"SRE does not belong to user's orgs", 403)
    return sre


def save_sre(sre: StructuredResponseEndpoint) -> StructuredResponseEndpoint:
    sre.updated_at = int(datetime.now().timestamp())
    put_item(SRE_TABLE_NAME, sre.model_dump())
    return sre


def delete_sre(sre_id: str) -> None:
    delete_item(SRE_TABLE_NAME, SRE_PRIMARY_KEY, sre_id)


def get_sres_for_org(org_id: str) -> list[StructuredResponseEndpoint]:
    return [StructuredResponseEndpoint(**item) for item in get_all_items_by_index(SRE_TABLE_NAME, "org_id", org_id)]
