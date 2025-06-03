import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json

def lambda_handler(event, context):
    user_pool_id = 'us-east-1_l8Fw4ESc3'  # Replace with your User Pool ID

    # Extract userID from query string parameters
    user_id = event.get('queryStringParameters', {}).get('userID')

    # Extract attributes from the serialized event body
    try:
        body = event['body']
        attributes = body.get('attributes')
    except:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid JSON body.',
                'event': event
            })
        }

    if not user_id or not attributes or not isinstance(attributes, dict):
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid input. Please provide userID in query string and attributes in the request body.'
            })
        }

    # Initialize the Cognito Identity Provider and DynamoDB clients
    cognito_client = boto3.client('cognito-idp')
    dynamodb_client = boto3.client('dynamodb')

    try:
        # Fetch the username from the DynamoDB Users table using the userID-index
        response = dynamodb_client.query(
            TableName='Users',
            IndexName='userID-index',
            KeyConditionExpression='userID = :userID',
            ExpressionAttributeValues={
                ':userID': {'S': user_id}
            }
        )

        if 'Items' not in response or not response['Items']:
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': f'User with userID {user_id} not found.'
                })
            }

        # Extract the username from the query result
        username = response['Items'][0]['username']['S']

        # Convert attributes to the required format
        user_attributes = [
            {'Name': key, 'Value': value}
            for key, value in attributes.items()
        ]

        # Update the user in the Cognito User Pool
        cognito_client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=username,
            UserAttributes=user_attributes
        )

        # Update the details in the DynamoDB Users table
        dynamodb_update_expression = "SET " + ", ".join(f"#attr_{i} = :val_{i}" for i in range(len(attributes)))
        expression_attribute_names = {f"#attr_{i}": key for i, key in enumerate(attributes.keys())}
        expression_attribute_values = {f":val_{i}": {'S': value} for i, value in enumerate(attributes.values())}

        dynamodb_client.update_item(
            TableName='Users',
            Key={'username': {'S': username}},
            UpdateExpression=dynamodb_update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'User {username} updated successfully.'
            })
        }

    except (BotoCoreError, ClientError) as error:
        print(f'Error updating user: {error}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to update user details.',
                'error': str(error),
                'event': event
            })
        }

# def mock_lambda_handler():
#     # Mock event with query string parameters and body
#     mock_event = {
#         'queryStringParameters': {
#             'userID': '0408e418-e061-7026-a190-dfd66d5734dc'
#         },
#         'body': json.dumps({
#             'attributes': {
#                 'email': 'test_finael@example.com',
#                 'name': 'Alon User',
#                 'phone_number': '+4564567890'
#             }
#         })
#     }
    
#     # Mock context
#     mock_context = {}
    
#     # Call lambda handler with mock data
#     result = lambda_handler(mock_event, mock_context)
#     print(result)

# if __name__ == '__main__':
#     mock_lambda_handler()