import boto3
from botocore.exceptions import ClientError
import json

def lambda_handler(event, context):
    # Initialize the DynamoDB client
    dynamodb = boto3.client('dynamodb')

    # Table and index names
    table_name = 'TransactionHistory'
    index_name = 'buyerID-index'

    # Validate input from query string parameters
    if 'queryStringParameters' not in event or not event['queryStringParameters'] or 'buyerID' not in event['queryStringParameters']:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'buyerID is required as a query string parameter.'})
        }

    buyer_id = event['queryStringParameters']['buyerID']

    try:
        # Query the table using the GSI
        response = dynamodb.query(
            TableName=table_name,
            IndexName=index_name,
            KeyConditionExpression='buyerID = :buyer_id',
            FilterExpression='#status = :pending_status',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':buyer_id': {'S': buyer_id},
                ':pending_status': {'S': 'pending'}
            }
        )

        # Extract and format the itemIDs
        item_ids = [
            item['ItemID']['S']
            for item in response.get('Items', [])
        ]

        return {
            'statusCode': 200,
            'body': json.dumps({'itemIDs': item_ids})
        }

    except ClientError as e:
        # Handle potential DynamoDB client errors
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Error querying transactions.', 'error': str(e)})
        }

# def mock_lambda_handler():
#     # Mock event with query string parameters
#     mock_event = {
#         'queryStringParameters': {
#             'buyerID': '0408e418-e061-7026-a190-dfd66d5734dc'
#         }
#     }
    
#     # Mock context object
#     mock_context = {}
    
#     # Call the lambda handler with mock data
#     result = lambda_handler(mock_event, mock_context)
#     print(result)

# if __name__ == "__main__":
#     mock_lambda_handler()