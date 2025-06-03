import boto3
from botocore.exceptions import BotoCoreError, ClientError
import json

def lambda_handler(event, context):
    user_pool_id = 'us-east-1_dhjcBYrYa'  # Replace with your User Pool ID

    # Extract old and new usernames from the request body
    try:
        body = json.loads(event.get('body', '{}'))
        old_username = body.get('old_username')
        new_username = body.get('new_username')
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid JSON body.'
            })
        }

    if not old_username or not new_username:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid input. Please provide both old_username and new_username.'
            })
        }

    # Initialize the Cognito Identity Provider client
    client = boto3.client('cognito-idp')

    try:
        # Update the preferred_username attribute to the new username
        client.admin_update_user_attributes(
            UserPoolId=user_pool_id,
            Username=old_username,
            UserAttributes=[
                {'Name': 'preferred_username', 'Value': new_username}
            ]
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Username for {old_username} updated to {new_username} successfully.'
            })
        }

    except (BotoCoreError, ClientError) as error:
        print(f'Error changing username: {error}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Failed to change username.',
                'error': str(error)
            })
        }

def mock_lambda_handler():
    # Mock event with sample data
    mock_event = {
        'body': json.dumps({
            'old_username': 'alon',
            'new_username': 'john.smith'
        })
    }
    
    # Mock context object
    class MockContext:
        def __init__(self):
            self.function_name = "update_username"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:update_username"
            self.memory_limit_in_mb = 128
            self.aws_request_id = "52fdfc07-2182-154f-163f-5f0f9a621d72"
            self.log_group_name = "/aws/lambda/update_username"
            self.log_stream_name = "2020/01/31/[$LATEST]92cac3de4371446fab648e634b0f6c18"
            
    mock_context = MockContext()
    
    # Call the lambda handler with mock data
    result = lambda_handler(mock_event, mock_context)
    print(result)

if __name__ == "__main__":
    mock_lambda_handler()