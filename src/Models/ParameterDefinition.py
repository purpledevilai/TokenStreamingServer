import os
from datetime import datetime
import uuid
from AWS.DynamoDB import get_item, put_item, delete_item, get_all_items_by_index
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Type
from Models import User


PARAMETER_DEFINITIONS_TABLE_NAME = os.environ["PARAMETER_DEFINITIONS_TABLE_NAME"]
PARAMETER_DEFINITIONS_PRIMARY_KEY = os.environ["PARAMETER_DEFINITIONS_PRIMARY_KEY"]

class ParamType(str, Enum):
    string = "string"
    number = "number"
    boolean = "boolean"
    object = "object"
    array = "array"
    enum = "enum"

class Parameter(BaseModel):
    name: str
    description: str
    type: ParamType
    parameters: list["Parameter"] = []

class ParameterDefinition(BaseModel):
    pd_id: str
    org_id: str
    parameters: list[Parameter]
    created_at: int
    updated_at: int

class CreateParameterDefinitionParams(BaseModel):
    org_id: Optional[str] = None
    parameters: list[dict]

class UpdateParameterDefinitionParams(BaseModel):
    parameters: list[dict]


def parameter_definition_exists(pd_id: str) -> bool:
    return get_item(PARAMETER_DEFINITIONS_TABLE_NAME, PARAMETER_DEFINITIONS_PRIMARY_KEY, pd_id) != None

def create_parameter_definition(
        org_id: str,
        parameters: list[dict],
    ) -> ParameterDefinition:
    pd_id = str(uuid.uuid4())
    created_at = int(datetime.now().timestamp())
    updated_at = created_at
    parameter_definition = ParameterDefinition(
        pd_id=pd_id,
        org_id=org_id,
        parameters=parameters,
        created_at=created_at,
        updated_at=updated_at
    )
    put_item(PARAMETER_DEFINITIONS_TABLE_NAME, parameter_definition.model_dump())
    return parameter_definition

def get_parameter_definition(pd_id: str) -> ParameterDefinition:
    item = get_item(PARAMETER_DEFINITIONS_TABLE_NAME, PARAMETER_DEFINITIONS_PRIMARY_KEY, pd_id)
    if item == None:
        raise Exception(f"ParameterDefinition {pd_id} not found", 404)
    return ParameterDefinition(**item)

def get_parameter_definition_for_user(pd_id: str, user: User.User) -> ParameterDefinition:
    parameter_definition = get_parameter_definition(pd_id)
    if (parameter_definition.org_id not in user.organizations):
        raise Exception(f"Parameter definition does not belong to user's orgs", 403)
    return parameter_definition

def save_parameter_definition(parameter_definition: ParameterDefinition) -> ParameterDefinition:
    parameter_definition.updated_at = int(datetime.now().timestamp())
    put_item(PARAMETER_DEFINITIONS_TABLE_NAME, parameter_definition.model_dump())
    return parameter_definition

def delete_parameter_definition(pd_id: str) -> None:
    delete_item(PARAMETER_DEFINITIONS_TABLE_NAME, PARAMETER_DEFINITIONS_PRIMARY_KEY, pd_id)

def get_parameter_definitions_for_org(org_id: str) -> list[ParameterDefinition]:
    return [ParameterDefinition(**item) for item in get_all_items_by_index(PARAMETER_DEFINITIONS_TABLE_NAME, "org_id", org_id)]

def create_pydantic_class(name, parameters: list[Parameter], for_array=False, docstring='') -> Type[BaseModel]:
  attributes = {"__annotations__": {}}
  
  if docstring:
        attributes["__doc__"] = docstring
  
  for param in parameters:
    attributes[param.name] = Field(description=param.description)
    param_type = str
    if (param.type == ParamType.number):
      param_type = float
    elif (param.type == ParamType.boolean):
      param_type = bool
    elif (param.type == ParamType.object):
      param_type = create_pydantic_class(param.name, param.parameters, docstring=param.description)
    elif (param.type == ParamType.enum):
      param_type = Enum(param.name, {p.name: p.name for p in param.parameters})
    elif (param.type == ParamType.array):
      array_param = param.parameters[0]
      param_type = list[create_pydantic_class(array_param.name, param.parameters, for_array=True)]

    if for_array:
      return param_type
    
    attributes["__annotations__"][param.name] = param_type
  return type(name, (BaseModel,), attributes)