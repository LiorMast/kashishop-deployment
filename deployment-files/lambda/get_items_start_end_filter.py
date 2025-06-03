import boto3
import json


def get_filtered_items_range(table_name, start_index, end_index, filter_attribute=None, filter_value=None):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    items = []
    last_evaluated_key = None
    
    # Prepare base scan parameters
    scan_kwargs = {
        'Limit': end_index - start_index
    }
    
    # Add filtering if specified
    if filter_attribute and filter_value:
        scan_kwargs.update({
            'FilterExpression': '#attr = :val',
            'ExpressionAttributeNames': {
                '#attr': filter_attribute
            },
            'ExpressionAttributeValues': {
                ':val': filter_value
            }
        })
    
    try:
        while len(items) < (end_index - start_index):
            # if last_evaluated_key:
            scan_kwargs['ExclusiveStartKey'] = start_index
                
            response = table.scan(**scan_kwargs)
            items.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            
            if not last_evaluated_key:
                break
        
        # Slice the results to get the requested range
        start_pos = start_index
        end_pos = min(end_index, len(items))
        result_items = items[start_pos:end_pos]
        
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            
            'items': json.dumps({result_items}),
            'count': len(result_items),
            'has_more': last_evaluated_key is not None
        
        }
                
                
        # return {
        #     'items': result_items,
        #     'count': len(result_items),
        #     'has_more': last_evaluated_key is not None
        # }
        
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
        
# if __name__ == "__main__":
    # Mock event and context for local testing
    # mock_event = {
    #     'queryStringParameters': {
    #         'table_name': 'Items',
    #         'start': '5',
    #         'end': '6'
    #     }
    # }
    # mock_context = {}

    # Print the function's response
    # print(get_filtered_items_range('Items', 5, 6))