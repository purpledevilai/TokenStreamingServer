import json
import decimal
from typing import TypedDict
from enum import Enum


# Dumb thing to handle decimal types
def default_type_error_handler(obj):
    if isinstance(obj, decimal.Decimal):
        return int(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise Exception(f"Object of type {type(obj)} with value of {repr(obj)} is not JSON serializable")

class APIGatewayResponse(TypedDict):
    statusCode: int
    headers: dict
    body: str

def create_api_gateway_response(status_code, body, return_type) -> APIGatewayResponse:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": return_type,
            "Access-Control-Allow-Origin": "*",  # Allow requests from any origin
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",  # Allow these headers
            "Access-Control-Allow-Methods": "OPTIONS,POST,GET"  # Allow specific methods
        },
        "body": json.dumps(body, default=default_type_error_handler) if return_type == 'application/json' else body
    }
