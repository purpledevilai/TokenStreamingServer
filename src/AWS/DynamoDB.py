import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

def float_to_decimal(obj):
    """Recursively convert float objects to Decimal for DynamoDB serialization."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {key: float_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(item) for item in obj]
    else:
        return obj

def get_item(table_name: str, primary_key_name: str, key: str) -> dict:
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.get_item(Key={primary_key_name: key})
    if "Item" not in response:
        return None
    return response["Item"]

def get_items_by_scan(table_name: str, primary_key_name: str, keys: list[str]) -> list[dict]:
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.scan(
        FilterExpression=Attr(primary_key_name).is_in(keys)
    )
    return response.get('Items', [])

def get_all_items(table_name: str) -> list[dict]:
    table = boto3.resource("dynamodb").Table(table_name)
    response = table.scan()
    return response['Items']

def put_item(table_name: str, item: dict) -> None:
    table = boto3.resource("dynamodb").Table(table_name)
    # Convert floats to Decimals for DynamoDB compatibility
    converted_item = float_to_decimal(item)
    table.put_item(Item=converted_item)

def update_item(table_name: str, primary_key_name: str, key: str, update_attributes: dict) -> dict:
    item = get_item(table_name, primary_key_name, key)
    item.update(update_attributes)
    put_item(table_name, item)
    return item
    

def delete_item(table_name: str, primary_key_name: str, key: str) -> None:
    table = boto3.resource("dynamodb").Table(table_name)
    table.delete_item(Key={primary_key_name: key})

def get_all_items_by_index(table_name: str, index_key: str, key_value: str) -> list[dict]:
    """
    Query items by an index, assuming the index name matches the index key.

    :param table_name: Name of the DynamoDB table
    :param index_key: The key for the GSI and also the index name
    :param key_value: Value of the key to query
    :return: List of items matching the query
    """
    table = boto3.resource("dynamodb").Table(table_name)
    items = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = table.query(
                IndexName=index_key,
                KeyConditionExpression=Key(index_key).eq(key_value),
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = table.query(
                IndexName=index_key,
                KeyConditionExpression=Key(index_key).eq(key_value)
            )

        items.extend(response.get('Items', []))

        if 'LastEvaluatedKey' in response:
            last_evaluated_key = response['LastEvaluatedKey']
        else:
            break

    return items

def get_latest_items_by_index(
    table_name: str,
    index_name: str,
    index_key: str,
    index_value: str,
    limit: int
) -> list[dict]:
    """
    Get the latest N items from a DynamoDB table using a GSI with a partition key and a timestamp sort key.

    :param table_name: Name of the DynamoDB table
    :param index_name: Name of the GSI to use
    :param index_key: Partition key name for the index (e.g., 'org_id')
    :param index_value: Partition key value to query
    :param limit: Max number of items to return
    :return: List of matching items (sorted descending by timestamp)
    """
    table = boto3.resource("dynamodb").Table(table_name)

    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=Key(index_key).eq(index_value),
        ScanIndexForward=False,  # Get latest first
        Limit=limit
    )

    return response.get("Items", [])
