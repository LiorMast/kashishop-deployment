import boto3
import json

# Initialize DynamoDB and Cognito clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

# Configuration
USERS_TABLE_NAME = 'Users'
USER_ID_INDEX = 'userID-index'
USER_POOL_ID = 'us-east-1_l8Fw4ESc3'
ADMINS_GROUP = 'Admins'

def lambda_handler(event, context):
    try:
        # Extract userID from the query string parameters
        user_id = event['queryStringParameters']['userID']

        # Access the Users table
        users_table = dynamodb.Table(USERS_TABLE_NAME)

        # Query the DynamoDB table using the userID index
        response = users_table.query(
            IndexName=USER_ID_INDEX,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('userID').eq(user_id)
        )

        # Validate that the user exists
        if not response['Items']:
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'User not found in the database.'})
            }

        # Extract the username from the query result
        username = response['Items'][0]['username']

        # Check if the user is in the Admins group in Cognito
        cognito_response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=username
        )

        # Determine if the user belongs to the Admins group
        groups = [group['GroupName'] for group in cognito_response.get('Groups', [])]
        is_admin = ADMINS_GROUP in groups

        return {
            'statusCode': 200,
            'body': json.dumps({'isAdmin': is_admin})
        }

    except cognito_client.exceptions.UserNotFoundException:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'User not found in Cognito.'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'An error occurred.', 'error': str(e)})
        }

# def mock_lambda_handler():
#     # Mock event with query string parameters
#     mock_event = {
#         'queryStringParameters': {
#             'userID': '14e8e458-70e1-70a9-3ceb-315f812dd01f'
#         }
#     }
    
#     # Mock context object
#     mock_context = {}
    
#     # Call the lambda handler with mock data
#     result = lambda_handler(mock_event, mock_context)
#     print(result)

# if __name__ == '__main__':
#     mock_lambda_handler()