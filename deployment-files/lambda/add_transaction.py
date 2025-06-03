import boto3
import json
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')  # Update with your region
transaction_table_name = "TransactionHistory"  # Replace with your Transactions table name

def lambda_handler(event, context):
    try:
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Required fields for the transaction
        required_fields = ['transactionID', 'buyerID', 'sellerID', 'ItemID', 'transactionDate', 'price', 'status']
        
        # Validate input
        if not all(field in body for field in required_fields):
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                "body": json.dumps({"error": "Missing required fields in input."})
            }
        
        buyer_id = body['buyerID']
        item_id = body['ItemID']
        
        # DynamoDB table reference
        transaction_table = dynamodb.Table(transaction_table_name)
        
        # Query to check if a transaction with the same buyerID and ItemID exists
        response = transaction_table.scan(
            FilterExpression=Attr('buyerID').eq(buyer_id) & Attr('ItemID').eq(item_id)
        )
        
        if response.get('Items'):
            existing_transaction = response['Items'][0]
            existing_status = existing_transaction.get('status', '').lower()
            
            if existing_status == "pending":
                # Send response for existing "pending" transaction
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization"
                    },
                    "body": json.dumps({
                        "message": "Transaction with this buyerID and ItemID already exists.",
                        "transactionExists": True
                    })
                }
            elif existing_status == "rejected":
                # Send response for existing "rejected" transaction
                return {
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization"
                    },
                    "body": json.dumps({
                        "message": "The seller has rejected your offer for this product.",
                        "transactionExists": True
                    })
                }
        
        # If no such transaction exists, allow the transaction to be created
        transaction_table.put_item(Item=body)
        
        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({
                "message": "Transaction created successfully.",
                "transactionExists": False
            })
        }
    
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            "body": json.dumps({"error": "Failed to create transaction", "details": str(e)})
        }
