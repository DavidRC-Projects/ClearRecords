"""
Lambda handler for Audit Engine Function

Receives extracted document data and performs rules-based audit
against HCPC record-keeping standards.
"""

import json
import os
import logging
from audit_rules import AuditEngine

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Import security headers from document-processing (or define here)
def get_security_headers():
    """Return security headers for all responses"""
    return {
        'Content-Type': 'application/json',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Cache-Control': 'no-store, no-cache, must-revalidate, private',
        'Pragma': 'no-cache'
    }

def get_cors_headers(event):
    """Get CORS headers based on request"""
    headers = get_security_headers()
    
    # Get allowed origins from environment
    allowed_origins_raw = os.environ.get('ALLOWED_ORIGINS', '')
    allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(',') if origin.strip()]
    
    # Get origin from request
    request_headers = event.get('headers', {}) or {}
    origin = request_headers.get('origin') or request_headers.get('Origin', '')
    
    if origin in allowed_origins:
        headers['Access-Control-Allow-Origin'] = origin
        headers['Access-Control-Allow-Credentials'] = 'true'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    elif os.environ.get('ENVIRONMENT', 'production').lower() == 'development':
        headers['Access-Control-Allow-Origin'] = '*'
    else:
        headers['Access-Control-Allow-Origin'] = 'null'
    
    return headers

def error_response(status_code, error, message, event, context=None):
    """Create standardized error response"""
    request_id = context.aws_request_id if context else 'unknown'
    
    logger.error(f"Error in audit engine: {error}", extra={
        'request_id': request_id,
        'status_code': status_code,
        'error_type': error
    })
    
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(event),
        'body': json.dumps({
            'success': False,
            'error': error,
            'message': message
        })
    }

def lambda_handler(event, context):
    """
    Lambda handler for audit engine
    
    Receives extracted document data and performs rules-based audit
    Returns audit results with findings and recommendations
    """
    request_id = context.aws_request_id if context else 'unknown'
    
    try:
        # Validate event structure
        if not isinstance(event, dict):
            return error_response(400, 'Invalid request format', 'Event must be a dictionary', event, context)
        
        # Log request start
        logger.info(f"Audit request started", extra={
            'request_id': request_id
        })
        
        # Parse request body
        body = {}
        if 'body' in event:
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            elif isinstance(event.get('body'), dict):
                body = event['body']
        
        if not isinstance(body, dict):
            body = {}
        
        # Get extracted data from request
        extracted_data = body.get('extracted_data', {})
        
        # Validate extracted data structure
        if not isinstance(extracted_data, dict):
            return error_response(400, 'Invalid extracted_data format',
                               'extracted_data must be a dictionary with text, tables, and forms',
                               event, context)
        
        # Validate required fields
        if 'text' not in extracted_data:
            return error_response(400, 'Missing required field',
                               'extracted_data must include "text" field',
                               event, context)
        
        # Initialize audit engine
        try:
            audit_engine = AuditEngine()
        except Exception as e:
            logger.error(f"Failed to initialize AuditEngine: {e}", extra={
                'request_id': request_id,
                'error': str(e)
            })
            return error_response(500, 'Initialization error',
                                'Failed to initialize audit engine',
                                event, context)
        
        # Perform audit
        try:
            audit_results = audit_engine.audit_document(extracted_data)
        except Exception as e:
            logger.error(f"Audit processing failed: {e}", extra={
                'request_id': request_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return error_response(500, 'Audit processing failed',
                                'An error occurred during audit processing',
                                event, context)
        
        # Log successful audit
        logger.info(f"Audit completed successfully", extra={
            'request_id': request_id,
            'overall_status': audit_results.get('overall_status'),
            'findings_count': len(audit_results.get('findings', [])),
            'strengths_count': len(audit_results.get('strengths', []))
        })
        
        # Return audit results
        return {
            'statusCode': 200,
            'headers': get_cors_headers(event),
            'body': json.dumps({
                'success': True,
                'message': 'Audit completed successfully',
                'data': audit_results
            })
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing error: {e}", extra={
            'request_id': request_id
        })
        return error_response(400, 'Invalid JSON in request body',
                            'Request body must be valid JSON',
                            event, context)
    
    except Exception as e:
        logger.error(f"Unexpected error in audit handler: {e}", extra={
            'request_id': request_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        return error_response(500, 'Internal server error',
                            'An unexpected error occurred',
                            event, context)
