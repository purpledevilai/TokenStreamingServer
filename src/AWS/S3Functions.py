import boto3

def get_text_from_file(bucket_name: str, key: str):
    s3 = boto3.client('s3')
    s3_response = s3.get_object(Bucket=bucket_name, Key=key)
    text_from_file = s3_response['Body'].read().decode('utf-8')
    return text_from_file