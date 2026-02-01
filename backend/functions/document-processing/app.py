import json
import re
import os
import sys
import logging
from texttract_processor import TextractProcessor

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Security constants
MAX_S3_KEY_LENGTH = 1024  # S3 key max length
MAX_BODY_SIZE = 10 * 1024  # 10KB max request body size
# S3 key allowed characters: alphanumeric, spaces, and: ! - _ . * ' ( ) /
# Note: Single quote in character class doesn't need escaping
ALLOWED_S3_KEY_PATTERN = re.compile(r'^[a-zA-Z0-9!_.*\'()\s/-]+$')  # Safe S3 key characters

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

def get_cors_origin(event):
    """Get allowed CORS origin based on request and configuration"""
    # Fix: Strip whitespace from origins
    allowed_origins_raw = os.environ.get('ALLOWED_ORIGINS', '')
    allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(',') if origin.strip()]
    
    if not allowed_origins:
        # Default: no CORS in production, allow all in dev
        if os.environ.get('ENVIRONMENT', 'production').lower() == 'development':
            return '*'
        return 'null'
    
    # Get origin from request
    headers = event.get('headers', {}) or {}
    origin = headers.get('origin') or headers.get('Origin', '')
    
    # Check if origin is allowed
    if origin in allowed_origins:
        return origin
    
    # No origin or not allowed - return null
    return 'null'

def get_cors_headers(event):
    """Get CORS headers based on request"""
    origin = get_cors_origin(event)
    headers = get_security_headers()
    headers['Access-Control-Allow-Origin'] = origin
    # Fix: Don't set credentials with wildcard origin (browser security violation)
    if origin != 'null' and origin != '*':
        headers['Access-Control-Allow-Credentials'] = 'true'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return headers

def get_user_id(event):
    """Extract user ID from authentication context"""
    try:
        request_context = event.get('requestContext', {})
        authorizer = request_context.get('authorizer', {})
        claims = authorizer.get('claims', {})
        return claims.get('sub') or claims.get('user_id') or 'anonymous'
    except Exception:
        return 'anonymous'

def sanitize_error_message(error_msg, is_dev=False):
    """Sanitize error messages to prevent information disclosure"""
    if is_dev:
        return str(error_msg)
    
    # Filter out sensitive AWS error details
    sensitive_patterns = [
        r'AccessDenied',
        r'InvalidParameter',
        r'NoSuchBucket',
        r'403',
        r'arn:aws:',
        r'us-east-\d',
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, str(error_msg), re.IGNORECASE):
            return 'Document processing failed. Please verify the document exists and is accessible.'
    
    return 'An internal error occurred'

def error_response(status_code, error, message, event, context=None):
    """Create standardized error response with security headers"""
    request_id = context.aws_request_id if context else 'unknown'
    
    # Fix: Handle case where event is not a dict (e.g., invalid event structure)
    if isinstance(event, dict):
        user_id = get_user_id(event)
        cors_headers = get_cors_headers(event)
    else:
        user_id = 'unknown'
        # Use default headers if event is invalid
        cors_headers = get_security_headers()
        cors_headers['Access-Control-Allow-Origin'] = 'null'
    
    # Log error (without sensitive data)
    logger.error(f"Error in document processing", extra={
        'request_id': request_id,
        'user_id': user_id,
        'status_code': status_code,
        'error_type': error
    })
    
    return {
        'statusCode': status_code,
        'headers': cors_headers,
        'body': json.dumps({
            'success': False,
            'error': error,
            'message': message
        })
    }

def lambda_handler(event, context):
    """
    Lambda handler for document processing
    
    Receives requests to process documents from S3 using AWS Textract
    Returns extracted text and structured data
    
    Security Features:
    - Authentication verification
    - CORS origin validation
    - S3 key ownership validation
    - Request size limits
    - Error message sanitization
    - Audit logging
    """
    request_id = context.aws_request_id if context else 'unknown'
    user_id = 'anonymous'
    is_dev = os.environ.get('ENVIRONMENT', 'production').lower() in ['dev', 'development']
    
    try:
        # Validate event structure
        if not isinstance(event, dict):
            return error_response(400, 'Invalid request format', 'Event must be a dictionary', event, context)
        
        # Security: Verify authentication
        user_id = get_user_id(event)
        if user_id == 'anonymous':
            # Check if authentication is required
            if os.environ.get('REQUIRE_AUTH', 'true').lower() == 'true':
                logger.warning(f"Unauthenticated request attempt", extra={'request_id': request_id})
                return error_response(401, 'Unauthorized', 'Authentication required', event, context)
        
        # Log request start (audit trail)
        logger.info(f"Document processing request started", extra={
            'request_id': request_id,
            'user_id': user_id,
            'timestamp': context.get_remaining_time_in_millis() if context else None
        })
        
        # Fix: Validate request body size BEFORE parsing (check both string and dict)
        body_str = event.get('body', '')
        if isinstance(body_str, str):
            if len(body_str) > MAX_BODY_SIZE:
                return error_response(413, 'Request too large', 
                                   f'Request body exceeds maximum size of {MAX_BODY_SIZE} bytes', event, context)
        elif isinstance(body_str, dict):
            # Estimate dict size using JSON serialization (more accurate than sys.getsizeof)
            try:
                dict_json = json.dumps(body_str)
                dict_size = len(dict_json.encode('utf-8'))
            except (TypeError, ValueError):
                # Fallback to string representation if JSON serialization fails
                dict_size = len(str(body_str).encode('utf-8'))
            if dict_size > MAX_BODY_SIZE:
                return error_response(413, 'Request too large', 
                                   f'Request body exceeds maximum size of {MAX_BODY_SIZE} bytes', event, context)
        
        # Parse the request body
        body = {}
        if 'body' in event:
            if isinstance(event.get('body'), str):
                # JSON parsing errors will be caught by JSONDecodeError handler below
                body = json.loads(event['body'])
            elif isinstance(event.get('body'), dict):
                body = event['body']
            # If body is None or other type, body remains {}
        
        # Ensure body is a dictionary (in case JSON parsing returned non-dict)
        if not isinstance(body, dict):
            body = {}
        
        # Get the S3 key from the request
        s3_key = body.get('s3_key')
        
        # Validate s3_key is a non-empty string
        if not s3_key or not isinstance(s3_key, str) or not s3_key.strip():
            return error_response(400, 'Missing or invalid parameter: s3_key',
                                'Please provide a valid S3 key (non-empty string) of the document to process',
                                event, context)
        
        # Strip whitespace from s3_key
        s3_key = s3_key.strip()
        
        # Security: Validate S3 key format to prevent path traversal and injection attacks
        if len(s3_key) > MAX_S3_KEY_LENGTH:
            return error_response(400, 'Invalid S3 key',
                                f'S3 key exceeds maximum length of {MAX_S3_KEY_LENGTH} characters',
                                event, context)
        
        # Prevent path traversal attacks (../, ..\, etc.)
        if '..' in s3_key or s3_key.startswith('/') or '//' in s3_key:
            return error_response(400, 'Invalid S3 key',
                                'S3 key contains invalid characters or path traversal attempts',
                                event, context)
        
        # Validate S3 key contains only safe characters
        if not ALLOWED_S3_KEY_PATTERN.match(s3_key):
            return error_response(400, 'Invalid S3 key',
                                'S3 key contains invalid characters',
                                event, context)
        
        # Security: Validate S3 key ownership (user can only access their own files)
        expected_prefix = os.environ.get('S3_KEY_PREFIX', '')
        if expected_prefix:
            # If prefix is configured, validate S3 key starts with it
            if not s3_key.startswith(expected_prefix):
                logger.warning(f"S3 key prefix validation failed", extra={
                    'request_id': request_id,
                    'user_id': user_id,
                    's3_key_prefix': s3_key[:20] + '...' if len(s3_key) > 20 else s3_key
                })
                return error_response(403, 'Access denied',
                                    'S3 key does not match expected pattern',
                                    event, context)
        
        # Fix: Use path-based validation instead of substring matching
        # Additional ownership check: if user_id is available, validate it's in the path
        if user_id != 'anonymous':
            # Check if user-based validation is enabled
            if os.environ.get('VALIDATE_USER_OWNERSHIP', 'true').lower() == 'true':
                # Use path-based validation, not substring matching
                expected_user_path = f"uploads/{user_id}/"
                if not s3_key.startswith(expected_user_path):
                    logger.warning(f"User ownership validation failed", extra={
                        'request_id': request_id,
                        'user_id': user_id,
                        's3_key_prefix': s3_key[:20] + '...' if len(s3_key) > 20 else s3_key,
                        'expected_path': expected_user_path
                    })
                    return error_response(403, 'Access denied',
                                        'You can only access your own documents',
                                        event, context)
        
        # Initialize the Textract processor
        try:
            processor = TextractProcessor()
        except Exception as e:
            logger.error(f"Failed to initialize TextractProcessor", extra={
                'request_id': request_id,
                'user_id': user_id,
                'error': str(e) if is_dev else 'Initialization failed'
            })
            return error_response(500, 'Initialization error',
                                sanitize_error_message(str(e), is_dev),
                                event, context)
        
        # Process the document
        result = processor.process_document(s3_key)
        
        # Validate result structure
        if not isinstance(result, dict):
            logger.error(f"Invalid result format from processor", extra={
                'request_id': request_id,
                'user_id': user_id
            })
            return error_response(500, 'Document processing failed',
                                'Invalid response format from processor',
                                event, context)
        
        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error occurred')
            sanitized_msg = sanitize_error_message(error_msg, is_dev)
            
            logger.error(f"Document processing failed", extra={
                'request_id': request_id,
                'user_id': user_id,
                's3_key_prefix': s3_key[:20] + '...' if len(s3_key) > 20 else s3_key,
                'error': error_msg if is_dev else 'Processing failed'
            })
            
            return error_response(500, 'Document processing failed',
                                sanitized_msg,
                                event, context)
        
        # Fix: Add response size limits to prevent Lambda timeouts and memory issues
        MAX_RESPONSE_SIZE = 6 * 1024 * 1024  # 6MB (Lambda response limit)
        response_data = {
            'text': result.get('text', ''),
            'tables': result.get('tables', []),
            'forms': result.get('forms', [])
        }
        
        # Check total response size and truncate text if needed
        # Build response structure to estimate size
        response_structure = {
            'success': True,
            'message': 'Document processed successfully',
            'data': response_data
        }
        
        # Estimate JSON size (rough approximation)
        json_str = json.dumps(response_structure)
        json_size = len(json_str.encode('utf-8'))
        was_truncated = False
        
        if json_size > MAX_RESPONSE_SIZE:
            # Calculate how much we need to truncate
            # Leave room for JSON structure, tables, forms, and truncation message
            base_structure = {
                'success': True,
                'message': 'Document processed successfully',
                'data': {
                    'text': '',
                    'tables': response_data['tables'],
                    'forms': response_data['forms']
                }
            }
            base_size = len(json.dumps(base_structure).encode('utf-8'))
            available_for_text = MAX_RESPONSE_SIZE - base_size - 1000  # 1KB buffer for truncation message
            
            if available_for_text > 0:
                original_text = response_data['text']
                truncated_text = original_text[:available_for_text] + '\n...[truncated due to size limit]'
                response_data['text'] = truncated_text
                was_truncated = True
                logger.warning(f"Response text truncated due to size", extra={
                    'request_id': request_id,
                    'user_id': user_id,
                    'original_text_size': len(original_text),
                    'truncated_text_size': len(truncated_text),
                    'tables_count': len(response_data['tables']),
                    'forms_count': len(response_data['forms'])
                })
            else:
                # Even without text, response is too large - truncate tables/forms
                response_data['text'] = '[Response too large - content truncated]'
                response_data['tables'] = []
                response_data['forms'] = []
                was_truncated = True
                logger.error(f"Response exceeds size limit even without text", extra={
                    'request_id': request_id,
                    'user_id': user_id,
                    'estimated_size': json_size
                })
        
        # Log successful processing (audit trail)
        
        logger.info(f"Document processed successfully", extra={
            'request_id': request_id,
            'user_id': user_id,
            's3_key_prefix': s3_key[:20] + '...' if len(s3_key) > 20 else s3_key,
            'has_text': bool(response_data['text']),
            'text_size': len(response_data['text']),
            'tables_count': len(response_data['tables']),
            'forms_count': len(response_data['forms']),
            'was_truncated': was_truncated
        })
        
        # Return successful response with extracted data
        return {
            'statusCode': 200,
            'headers': get_cors_headers(event),
            'body': json.dumps({
                'success': True,
                'message': 'Document processed successfully',
                'data': response_data
            })
        }
        
    except json.JSONDecodeError as e:
        # Fix: Variables are always defined at function start, no need for locals() check
        # Handle JSON parsing errors - sanitize error message
        error_msg = str(e) if is_dev else 'Invalid JSON format in request body'
        
        logger.warning(f"JSON parsing error", extra={
            'request_id': request_id,
            'user_id': user_id,
            'error': str(e) if is_dev else 'Invalid JSON'
        })
        
        return error_response(400, 'Invalid JSON in request body',
                            error_msg,
                            event, context)
        
    except Exception as e:
        # Fix: Variables are always defined at function start, no need for locals() check
        # Handle any unexpected errors
        error_message = sanitize_error_message(str(e), is_dev)
        
        logger.error(f"Unexpected error in lambda handler", extra={
            'request_id': request_id,
            'user_id': user_id,
            'error': str(e) if is_dev else 'Unexpected error',
            'error_type': type(e).__name__
        })
        
        return error_response(500, 'Internal server error',
                            error_message,
                            event, context)
