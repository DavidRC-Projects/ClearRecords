import json

def lambda_handler(event, context):
    """
    Health check endpoint
    Returns API status for testing purposes
    """
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'ClearRecords API is running',
            'status': 'healthy'
        })
    }