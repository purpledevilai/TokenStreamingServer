import json
from pydantic import BaseModel
from typing import Optional
import boto3
import decimal
from enum import Enum

# Dumb thing to handle decimal types
def default_type_error_handler(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise Exception(f"Object of type {type(obj)} with value of {repr(obj)} is not JSON serializable")

class LambdaEvent(BaseModel):
    path: str
    httpMethod: str
    queryStringParameters: Optional[dict] = None
    requestParameters: Optional[dict] = {}
    headers: Optional[dict] = {}
    body: Optional[str] = None

def invoke_lambda(lambda_name: str, event: dict, invokation_type: str = "Event"):
    client = boto3.client('lambda')
    response = client.invoke(
        FunctionName=lambda_name,
        InvocationType=invokation_type,
        Payload=bytes(json.dumps(event, default=default_type_error_handler), 'utf-8')
    )
    if invokation_type == "RequestResponse":
        return json.loads(response["Payload"].read().decode("utf-8"))