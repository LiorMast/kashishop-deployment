import boto3
import json

# Initialize the Cognito client
cognito_client = boto3.client('cognito-idp', region_name='us-east-1')

# User pool ID
USER_POOL_ID = 'us-east-1_l8Fw4ESc3'
ADMINS_GROUP = 'Admins'


def lambda_handler(event, context):
    try:
        # Extract the identity of the caller
        caller_sub = event['requestContext']['authorizer']['claims']['sub']
        caller_username = event['requestContext']['authorizer']['claims']['cognito:username']
        caller_groups = event['requestContext']['authorizer']['claims'].get('cognito:groups', '')

        body = json.loads(event['body'])
        username_to_delete = body.get('username', caller_username)

        # Check if the caller is in the Admins group
        is_admin = ADMINS_GROUP in caller_groups

        # Restrict non-admin users to delete only themselves
        if not is_admin and username_to_delete != caller_username:
            return {
                'statusCode': 403,
                'body': json.dumps({'message': 'Unauthorized: Cannot delete other users.'})
            }

        # Delete the user from the Cognito User Pool
        cognito_client.admin_delete_user(
            UserPoolId=USER_POOL_ID,
            Username=username_to_delete
        )

        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'User {username_to_delete} has been deleted.'})
        }

    except cognito_client.exceptions.UserNotFoundException:
        return {
            'statusCode': 404,
            'body': json.dumps({'message': 'User not found.'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'An error occurred.', 'error': str(e)})
        }

def mock_lambda_event():
    return {
        'requestContext': {
            'authorizer': {
                'claims': {
                    'sub': 'test-sub-id',
                    'cognito:username': 'liortestuser',
                    'cognito:groups': ['Admins']
                }
            }
        },
        'body': json.dumps({
            'username': 'liortestuser'
        })
    }
