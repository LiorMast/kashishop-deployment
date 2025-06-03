import boto3
import json

def lambda_handler(event, context):
    """
    Lambda function to query items in a DynamoDB table by seller ID.
    
    Args:
        event: The event triggering the Lambda function, expected to contain
               `seller_id` in the query string parameters.
        context: Lambda Context runtime methods and attributes.

    Returns:
        A JSON-formatted dictionary with the status code and either the items or an error message.
    """
    dynamodb = boto3.resource('dynamodb')
    
    # Extracting parameters from the query string
    try:
        table_name = "Items"
        seller_id = str(event['queryStringParameters']['sellerID'])
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid input. Ensure seller_id is provided in query string parameters.'})
        }
    
    table = dynamodb.Table(table_name)
    
    try:
        response = table.query(
            IndexName='seller-creationDate-index',  # Adjust to match your DynamoDB table's GSI
            KeyConditionExpression='seller = :val1',
            ExpressionAttributeValues={
                ':val1': seller_id
            }
        )
        
        for item in response.get('Items', []):
            item['itemID'] = str(item['itemID'])  # Convert itemID to string for JSON serialization
            item['seller'] = str(item['seller'])  # Convert seller to string for JSON serialization
            item['price'] = str(item['price'])  # Convert price to string for JSON serialization
            
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': json.dumps({'error': str(e)}),
        }
        
        
                

    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps({
            'items': response.get('Items', []),
            'count': len(response.get('Items', []))
        })
    }

# def test_lambda_handler():
#     # Mock event with query string parameters
#     test_event = {
#         'queryStringParameters': {
#             'sellerID': 'a4f8b4f8-d061-70a5-bc97-fc9241908887'
#         }
#     }
    
#     # Mock Lambda context
#     test_context = {}
    
#     # Call handler
#     response = lambda_handler(test_event, test_context)
#     return response
    
#     # # Verify response format
#     # assert response['statusCode'] == 200
#     # assert 'headers' in response
#     # assert 'body' in response
    
#     # # Parse response body
#     # body = json.loads(response['body'])
#     # assert 'items' in body
#     # assert 'count' in body

# if __name__ == '__main__':
#     print(test_lambda_handler())