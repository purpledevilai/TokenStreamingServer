import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, put_item, delete_item, get_all_items_by_index
from pydantic import BaseModel
from typing import Optional

DATA_WINDOWS_TABLE_NAME = os.environ["DATA_WINDOWS_TABLE_NAME"]
DATA_WINDOWS_PRIMARY_KEY = os.environ["DATA_WINDOWS_PRIMARY_KEY"]

class DataWindow(BaseModel):
    data_window_id: str
    org_id: str
    name: Optional[str] = None
    description: Optional[str] = None
    data: str
    created_at: int
    updated_at: int

class CreateDataWindowParams(BaseModel):
    org_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    data: str

class UpdateDataWindowParams(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    data: Optional[str] = None

def data_window_exists(data_window_id: str) -> bool:
    return get_item(DATA_WINDOWS_TABLE_NAME, DATA_WINDOWS_PRIMARY_KEY, data_window_id) != None

def create_data_window(
    org_id: str,
    data: str,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> DataWindow:
    data_window_id = str(uuid.uuid4())
    created_at = int(datetime.now().timestamp())
    updated_at = created_at
    data_window = DataWindow(
        data_window_id=data_window_id,
        org_id=org_id,
        name=name,
        description=description,
        data=data,
        created_at=created_at,
        updated_at=updated_at
    )
    put_item(DATA_WINDOWS_TABLE_NAME, data_window.model_dump())
    return data_window

def get_data_window(data_window_id: str) -> DataWindow:
    item = get_item(DATA_WINDOWS_TABLE_NAME, DATA_WINDOWS_PRIMARY_KEY, data_window_id)
    if item is None:
        raise Exception(f"DataWindow with id: {data_window_id} does not exist", 404)
    return DataWindow(**item)

def get_data_window_for_org(data_window_id: str, org_id: str) -> DataWindow:
    data_window = get_data_window(data_window_id)
    if data_window.org_id != org_id:
        raise Exception(f"DataWindow {data_window_id} does not belong to organization {org_id}", 403)
    return data_window

def save_data_window(data_window: DataWindow) -> DataWindow:
    data_window.updated_at = int(datetime.now().timestamp())
    put_item(DATA_WINDOWS_TABLE_NAME, data_window.model_dump())
    return data_window

def delete_data_window(data_window_id: str) -> None:
    delete_item(DATA_WINDOWS_TABLE_NAME, DATA_WINDOWS_PRIMARY_KEY, data_window_id)

def get_data_windows_for_org(org_id: str) -> list[DataWindow]:
    items = get_all_items_by_index(DATA_WINDOWS_TABLE_NAME, "org_id", org_id)
    return [DataWindow(**item) for item in items]

