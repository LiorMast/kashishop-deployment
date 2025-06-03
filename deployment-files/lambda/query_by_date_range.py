import boto3
import json


def query_by_date_range(table_name, start_date=None, end_date=None, ascending=True):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    # Build the key condition expression
    condition = 'partition_key = :pk'
    expression_values = {
        ':pk': 'itemID'
    }
    
    if start_date and end_date:
        condition += ' AND creationDate BETWEEN :start AND :end'
        expression_values[':start'] = start_date
        expression_values[':end'] = end_date
    elif start_date:
        condition += ' AND creationDate >= :start'
        expression_values[':start'] = start_date
    elif end_date:
        condition += ' AND creationDate <= :end'
        expression_values[':end'] = end_date
    
    items = []
    last_evaluated_key = None
    
    while True:
        query_params = {
            'KeyConditionExpression': condition,
            'ExpressionAttributeValues': expression_values,
            'ScanIndexForward': ascending
        }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
            
        response = table.query(**query_params)
        items.extend(response.get('Items', []))
        
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    return items

if __name__ == "__main__":
    # Mock event and context for local testing
    

    # Print the function's response
    print(query_by_date_range("Items"))
