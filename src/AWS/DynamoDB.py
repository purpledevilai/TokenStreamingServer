import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.conditions import Attr

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
    table.put_item(Item=item)

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
    response = table.query(
        IndexName=index_key,
        KeyConditionExpression=Key(index_key).eq(key_value)
    )
    return response['Items']
