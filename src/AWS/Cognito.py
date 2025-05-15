import os
import boto3
from pydantic import BaseModel


class CognitoUser(BaseModel):
    email: str
    sub: str
    family_name: str
    given_name: str


def get_user_from_cognito(access_token: str) -> CognitoUser:
    cognito = boto3.client("cognito-idp")
    response = cognito.get_user(
        AccessToken=access_token
    )
    user_attributes = {attr['Name']: attr['Value']
                       for attr in response['UserAttributes']}
    return CognitoUser(**user_attributes)


def delete_user_from_cognito(user_id: str) -> None:
    cognito = boto3.client("cognito-idp")
    cognito.admin_delete_user(
        UserPoolId=os.environ["USER_POOL_ID"],
        Username=user_id
    )
