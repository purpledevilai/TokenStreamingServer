import os
import uuid
import json
from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel
from AWS.DynamoDB import (
    get_item,
    get_all_items_by_index,
    get_items_by_scan,
    put_item,
    delete_item,
)
from AWS.CloudWatchLogs import get_logger
from Models import User

logger = get_logger(log_level=os.environ["LOG_LEVEL"])

DOCUMENTS_TABLE_NAME = os.environ["JSON_DOCUMENTS_TABLE_NAME"]
DOCUMENTS_PRIMARY_KEY = os.environ["JSON_DOCUMENTS_PRIMARY_KEY"]  # likely "document_id"

# --------------------- Models ---------------------


class JSONDocument(BaseModel):
    document_id: str
    name: str = "Untitled Document"
    data: Dict[str, Any]
    org_id: str
    created_at: int
    updated_at: int
    is_public: bool = False


class CreateJSONDocumentParams(BaseModel):
    name: str
    data: Dict[str, Any]
    org_id: Optional[str] = None
    is_public: Optional[bool] = False


class UpdateJSONDocumentParams(BaseModel):
    data: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    name: Optional[str] = None


# --------------------- CRUD Functions ---------------------


def json_document_exists(document_id: str) -> bool:
    return (
        get_item(DOCUMENTS_TABLE_NAME, DOCUMENTS_PRIMARY_KEY, document_id) is not None
    )


def create_json_document(params: CreateJSONDocumentParams) -> JSONDocument:
    if params.org_id is None:
        raise Exception("Organization ID must be provided", 400)
    now = int(datetime.timestamp(datetime.now()))
    document_data = {
        DOCUMENTS_PRIMARY_KEY: str(uuid.uuid4()),
        "name": params.name,
        "data": params.data,
        "org_id": params.org_id,
        "is_public": params.is_public,
        "created_at": now,
        "updated_at": now,
    }
    document = JSONDocument(**document_data)
    put_item(DOCUMENTS_TABLE_NAME, document_data)
    return document


def get_json_document(document_id: str) -> JSONDocument:
    item = get_item(DOCUMENTS_TABLE_NAME, DOCUMENTS_PRIMARY_KEY, document_id)
    if item is None:
        raise Exception(f"JSONDocument with id: {document_id} does not exist", 404)
    if "name" not in item or item["name"] is None:
        item["name"] = f"Document {item[DOCUMENTS_PRIMARY_KEY]}"
        put_item(DOCUMENTS_TABLE_NAME, item)
    return JSONDocument(**item)


def get_public_json_document(document_id: str) -> JSONDocument:
    document = get_json_document(document_id)
    if document.is_public:
        return document
    raise Exception(f"Document is not public", 403)


def save_json_document(document: JSONDocument) -> None:
    document.updated_at = int(datetime.timestamp(datetime.now()))
    put_item(DOCUMENTS_TABLE_NAME, document.model_dump())


def delete_json_document(document_id: str) -> None:
    delete_item(DOCUMENTS_TABLE_NAME, DOCUMENTS_PRIMARY_KEY, document_id)


def get_json_document_for_user(document_id: str, user: User.User) -> JSONDocument:
    doc = get_json_document(document_id)
    if doc.is_public:
        return doc
    if doc.org_id in user.organizations:
        return doc
    raise Exception(f"Document does not belong to user's orgs", 403)


def parse_json_document_items(items: list[dict]) -> list[JSONDocument]:
    documents = []
    for item in items:
        try:
            if "name" not in item or item["name"] is None:
                item["name"] = f"Document {item[DOCUMENTS_PRIMARY_KEY]}"
                put_item(DOCUMENTS_TABLE_NAME, item)
            documents.append(JSONDocument(**item))
        except Exception as e:
            logger.error(f"Error parsing document: {e}")
    return documents


def get_json_documents_from_ids(document_ids: list[str]) -> list[JSONDocument]:
    items = get_items_by_scan(DOCUMENTS_TABLE_NAME, DOCUMENTS_PRIMARY_KEY, document_ids)
    return parse_json_document_items(items)


def get_json_documents_in_org(org_id: str) -> list[JSONDocument]:
    items = get_all_items_by_index(DOCUMENTS_TABLE_NAME, "org_id", org_id)
    return parse_json_document_items(items)


def delete_json_documents_in_org(org_id: str) -> None:
    documents = get_json_documents_in_org(org_id)
    for doc in documents:
        delete_json_document(doc.document_id)


# --------------------- Data Helpers ---------------------


def _parse_value(value: str, value_type: str):
    """Parse a string value into the correct python type."""
    if value_type == "string":
        return value
    if value_type == "boolean":
        val = value.lower()
        if val in ["true", "false"]:
            return val == "true"
        raise Exception("Invalid boolean value", 400)
    if value_type == "number":
        try:
            return int(value) if value.isdigit() else float(value)
        except ValueError:
            raise Exception("Invalid number value", 400)
    if value_type == "json":
        try:
            parsed = json.loads(value)
        except Exception:
            raise Exception("Invalid JSON value", 400)
        if not isinstance(parsed, (dict, list)):
            raise Exception("JSON value must be an object or list", 400)
        return parsed
    raise Exception("Invalid type", 400)


def _navigate_to_parent(data: Any, parts: list[str], create_missing: bool):
    """Navigate to the parent of the final segment in parts."""
    current = data
    for i, part in enumerate(parts[:-1]):
        next_part = parts[i + 1]
        if part.isdigit():
            index = int(part)
            if not isinstance(current, list):
                raise Exception(f"Expected list at {'.'.join(parts[:i])}", 400)
            if index >= len(current):
                raise Exception("List index out of range", 400)
            current = current[index]
        else:
            if not isinstance(current, dict):
                raise Exception(f"Expected object at {'.'.join(parts[:i])}", 400)
            if part not in current:
                if create_missing:
                    current[part] = [] if next_part.isdigit() else {}
                else:
                    raise Exception("Path not found", 404)
            current = current[part]
    return current, parts[-1]


def _resolve_path(data: Any, parts: list[str]):
    current = data
    for i, part in enumerate(parts):
        if part.isdigit():
            index = int(part)
            if not isinstance(current, list):
                raise Exception(f"Expected list at {'.'.join(parts[:i])}", 400)
            if index >= len(current):
                raise Exception("List index out of range", 400)
            current = current[index]
        else:
            if not isinstance(current, dict):
                raise Exception(f"Expected object at {'.'.join(parts[:i])}", 400)
            if part not in current:
                raise Exception("Path not found", 404)
            current = current[part]
    return current


def _infer_shape(value: Any):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)) or type(value).__name__ == "Decimal":
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return {k: _infer_shape(v) for k, v in value.items()}
    if isinstance(value, list):
        if not value:
            return []
        shapes = [_infer_shape(v) for v in value]
        object_shapes = [s for s in shapes if isinstance(s, dict)]
        non_obj_shapes = [s for s in shapes if not isinstance(s, dict)]
        result = []
        if object_shapes:
            keys = set().union(*(o.keys() for o in object_shapes))
            combined = {}
            for key in keys:
                key_shapes = [o[key] for o in object_shapes if key in o]
                shape_val = key_shapes[0]
                if not all(shape_val == s for s in key_shapes):
                    shape_val = "mixed"
                if not all(key in o for o in object_shapes):
                    shape_val = f"optional {shape_val}"
                combined[key] = shape_val
            result.append(combined)
        for s in non_obj_shapes:
            if s not in result:
                result.append(s)
        return result
    return "null"


# --------------------- Extended Functions ---------------------


def set_value(
    document_id: str, path: str, value: str, type: str, user: Optional[User.User] = None
) -> JSONDocument:
    document = (
        get_json_document_for_user(document_id, user)
        if user
        else get_public_json_document(document_id)
    )
    parsed = _parse_value(value, type)
    parent, last = _navigate_to_parent(document.data, path.split("."), True)
    if last.isdigit():
        idx = int(last)
        if not isinstance(parent, list):
            raise Exception("Expected list at final segment", 400)
        if idx >= len(parent):
            raise Exception("List index out of range", 400)
        parent[idx] = parsed
    else:
        if not isinstance(parent, dict):
            raise Exception("Expected object at final segment", 400)
        parent[last] = parsed
    save_json_document(document)
    return document


def add_list_item(
    document_id: str, path: str, value: str, type: str, user: Optional[User.User] = None
) -> JSONDocument:
    document = (
        get_json_document_for_user(document_id, user)
        if user
        else get_public_json_document(document_id)
    )
    parsed = _parse_value(value, type)
    parent, last = _navigate_to_parent(document.data, path.split("."), True)
    if last.isdigit():
        idx = int(last)
        if not isinstance(parent, list):
            raise Exception("Expected list at final segment", 400)
        if idx >= len(parent):
            raise Exception("List index out of range", 400)
        target = parent[idx]
    else:
        if not isinstance(parent, dict):
            raise Exception("Expected object at final segment", 400)
        if last not in parent:
            parent[last] = []
        target = parent[last]
    if not isinstance(target, list):
        raise Exception("Destination is not a list", 400)
    target.append(parsed)
    save_json_document(document)
    return document


def delete(
    document_id: str, path: str, user: Optional[User.User] = None
) -> JSONDocument:
    document = (
        get_json_document_for_user(document_id, user)
        if user
        else get_public_json_document(document_id)
    )
    parent, last = _navigate_to_parent(document.data, path.split("."), False)
    if last.isdigit():
        idx = int(last)
        if not isinstance(parent, list):
            raise Exception("Expected list at final segment", 400)
        if idx >= len(parent):
            raise Exception("List index out of range", 400)
        parent.pop(idx)
    else:
        if not isinstance(parent, dict):
            raise Exception("Expected object at final segment", 400)
        if last not in parent:
            raise Exception("Path not found", 404)
        del parent[last]
    save_json_document(document)
    return document


def get(document_id: str, path: str, user: Optional[User.User] = None):
    document = (
        get_json_document_for_user(document_id, user)
        if user
        else get_public_json_document(document_id)
    )
    value = _resolve_path(document.data, path.split("."))
    return value


def get_shape(document_id: str, user: Optional[User.User] = None) -> Dict[str, Any]:
    document = (
        get_json_document_for_user(document_id, user)
        if user
        else get_public_json_document(document_id)
    )
    return _infer_shape(document.data)
