import boto3
import json


# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # Get the table name from environment variables
    table_name = event['queryStringParameters'].get('table_name')

    # Access the DynamoDB table
    table = dynamodb.Table(table_name)

    try:
        # Get query parameters for pagination
        start_index = int(event['queryStringParameters'].get('start'))
        end_index = int(event['queryStringParameters'].get('end'))

        # Initialize scan parameters with limit and exclusive start key
        scan_kwargs = {
            'Limit': end_index - start_index
        }

        # Fetch items starting from the specified index
        items = []
        last_evaluated_key = None

        while len(items) < (end_index - start_index):
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key

            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            last_evaluated_key = response.get('LastEvaluatedKey')

            if not last_evaluated_key:
                break

        # Slice the items to ensure the correct range is returned
        selected_items = items[:end_index - start_index]

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps(selected_items)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'message': 'Error fetching items from DynamoDB',
                'error': str(e)
            })
        }

# # Example call to the function
# if __name__ == "__main__":
#     # Mock event and context for local testing
#     mock_event = {
#         'queryStringParameters': {
#             'table_name': 'Items',
#             'start': '5',
#             'end': '6'
#         }
#     }
#     mock_context = {}

#     # Print the function's response
#     print(lambda_handler(mock_event, mock_context))
