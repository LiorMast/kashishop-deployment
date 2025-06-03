import boto3
import json
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

def lambda_handler(event, context):
    # Initialize DynamoDB resources
    dynamodb = boto3.resource('dynamodb')
    transactions_table = dynamodb.Table('TransactionHistory')
    items_table = dynamodb.Table('Items')

    try:
        # Parse the request body
        body = json.loads(event.get('body', '{}'))
        
        # Validate required fields
        transaction_id = body.get('transactionID')
        new_status = body.get('status')

        if not transaction_id or new_status not in ['accepted', 'rejected']:
            return {
                'statusCode': 400,
                'headers': {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                'body': json.dumps({'error': 'transactionID and valid status (accepted/rejected) are required.'})
            }

        # Fetch the transaction details to get the ItemID
        transaction_response = transactions_table.get_item(Key={'transactionID': transaction_id})
        transaction = transaction_response.get('Item', {})
        
        if not transaction:
            return {
                'statusCode': 404,
                'headers': {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                'body': json.dumps({'error': 'Transaction not found.'})
            }
        
        item_id = transaction.get('ItemID')
        if not item_id:
            return {
                'statusCode': 400,
                'headers': {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                'body': json.dumps({'error': 'Transaction is missing ItemID.'})
            }

        # Update the transaction's status
        transactions_table.update_item(
            Key={'transactionID': transaction_id},
            UpdateExpression="SET #status = :new_status",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={':new_status': new_status},
            ConditionExpression="attribute_exists(transactionID)",
            ReturnValues="ALL_NEW"
        )

        if new_status == 'accepted':
            # Reject all other transactions with the same ItemID
            response = transactions_table.scan(
                FilterExpression=Attr('ItemID').eq(item_id) & Attr('transactionID').ne(transaction_id)
            )
            other_transactions = response.get('Items', [])
            for other_transaction in other_transactions:
                transactions_table.update_item(
                    Key={'transactionID': other_transaction['transactionID']},
                    UpdateExpression="SET #status = :rejected",
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={':rejected': 'rejected'}
                )

            # Update the item in the Items table
            items_table.update_item(
                Key={'itemID': item_id},
                UpdateExpression="SET isActive = :falseVal, isSold = :trueVal",
                ExpressionAttributeValues={
                    ':falseVal': "FALSE",
                    ':trueVal': "TRUE"
                },
                ConditionExpression="attribute_exists(itemID)"
            )

        # Return the success response
        return {
            'statusCode': 200,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            'body': json.dumps({'message': 'Transaction status updated successfully.'})
        }

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            return {
                'statusCode': 404,
                'headers': {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization"
                },
                'body': json.dumps({'error': 'Transaction or Item not found.'})
            }
        else:
            raise
    except Exception as e:
        # Log and return error details
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'headers': {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
                "Access-Control-Allow-Headers": "Content-Type, Authorization"
            },
            'body': json.dumps({'error': 'Failed to update transaction status', 'details': str(e)})
        }
