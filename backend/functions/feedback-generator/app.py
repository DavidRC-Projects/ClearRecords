"""
Lambda handler for Feedback Generator Function

Generates user-friendly feedback reports from audit results.
Feedback is educational, non-punitive, and references HCPC standards.
"""

import json
import os
import logging
import re
from datetime import datetime, timezone

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Security constants
MAX_BODY_SIZE = 5 * 1024 * 1024  # 5MB max request body size (prevents DoS)
MAX_RESPONSE_SIZE = 6 * 1024 * 1024  # 6MB max response size (prevents Lambda timeout)
MAX_FINDINGS_COUNT = 1000  # Maximum number of findings to process
MAX_NESTING_DEPTH = 10  # Maximum nesting depth for JSON structures

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
        # Security: Only set credentials for specific origins (not wildcard)
        headers['Access-Control-Allow-Credentials'] = 'true'
        headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    elif os.environ.get('ENVIRONMENT', 'production').lower() == 'development':
        headers['Access-Control-Allow-Origin'] = '*'
        # Security: Never set credentials with wildcard origin (browser security violation)
    else:
        headers['Access-Control-Allow-Origin'] = 'null'
    
    return headers

def sanitize_error_message(error_msg, is_dev=False):
    """Sanitize error messages to prevent information disclosure"""
    if is_dev:
        return str(error_msg)
    
    # Filter out sensitive internal details
    sensitive_patterns = [
        r'Traceback',
        r'File "',
        r'line \d+',
        r'AttributeError',
        r'TypeError',
        r'KeyError',
    ]
    
    error_str = str(error_msg)
    for pattern in sensitive_patterns:
        if re.search(pattern, error_str, re.IGNORECASE):
            return 'An internal error occurred during feedback generation'
    
    return 'An error occurred during feedback generation'

def error_response(status_code, error, message, event, context=None):
    """Create standardized error response with sanitized messages"""
    request_id = context.aws_request_id if context else 'unknown'
    
    # Determine if we're in development mode
    is_dev = os.environ.get('ENVIRONMENT', 'production').lower() == 'development'
    
    # Sanitize error message for production
    sanitized_message = sanitize_error_message(message, is_dev)
    
    logger.error(f"Error in feedback generator: {error}", extra={
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
            'message': sanitized_message
        })
    }

def generate_feedback_report(audit_results):
    """
    Generate user-friendly feedback report from audit results
    
    Args:
        audit_results: Dictionary containing audit results from AuditEngine
        
    Returns:
        Dictionary containing formatted feedback report
    """
    if not isinstance(audit_results, dict):
        raise ValueError("audit_results must be a dictionary")
    
    # Security: Validate and limit findings count to prevent DoS
    findings = audit_results.get('findings', [])
    if not isinstance(findings, list):
        findings = []
    
    # Limit findings count to prevent memory exhaustion
    if len(findings) > MAX_FINDINGS_COUNT:
        logger.warning(f"Findings count ({len(findings)}) exceeds maximum ({MAX_FINDINGS_COUNT}), truncating")
        findings = findings[:MAX_FINDINGS_COUNT]
    
    overall_status = audit_results.get('overall_status', 'unknown')
    strengths = audit_results.get('strengths', [])
    recommendations = audit_results.get('recommendations', [])
    summary = audit_results.get('summary', {})
    
    # Group findings by category for better organisation
    findings_by_category = {}
    for finding in findings:
        # Handle None, empty string, or non-string categories
        category_raw = finding.get('category')
        if not category_raw or not isinstance(category_raw, str):
            category = 'other'
        else:
            category = category_raw
        
        if category not in findings_by_category:
            findings_by_category[category] = []
        findings_by_category[category].append(finding)
    
    # Generate category summaries
    category_summaries = []
    for category, category_findings in findings_by_category.items():
        critical_count = sum(1 for f in category_findings if f.get('severity') == 'critical')
        warning_count = sum(1 for f in category_findings if f.get('severity') == 'warning')
        
        # Safely convert category to title case
        category_title = category.title() if isinstance(category, str) else str(category).title()
        
        category_summaries.append({
            'category': category_title,
            'total_issues': len(category_findings),
            'critical_issues': critical_count,
            'warnings': warning_count,
            'findings': category_findings
        })
    
    # Generate overall feedback message
    overall_message = _generate_overall_message(overall_status, summary)
    
    # Generate reflective prompts
    reflective_prompts = _generate_reflective_prompts(findings, strengths, overall_status)
    
    # Build feedback report
    feedback_report = {
        'generated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'overall_status': overall_status,
        'overall_message': overall_message,
        'summary': {
            'total_findings': summary.get('total_findings', 0),
            'critical_issues': summary.get('critical_issues', 0),
            'warnings': summary.get('warnings', 0),
            'strengths_count': summary.get('strengths_count', 0)
        },
        'findings': findings,  # Include all findings for reference
        'strengths': strengths,
        'category_summaries': category_summaries,
        'recommendations': recommendations,
        'reflective_prompts': reflective_prompts,
        'next_steps': _generate_next_steps(findings, overall_status)
    }
    
    return feedback_report

def _generate_overall_message(overall_status, summary):
    """Generate overall feedback message based on status"""
    # Handle None values safely
    critical_count = summary.get('critical_issues') or 0
    warning_count = summary.get('warnings') or 0
    strengths_count = summary.get('strengths_count') or 0
    
    # Ensure values are integers
    try:
        critical_count = int(critical_count) if critical_count is not None else 0
        warning_count = int(warning_count) if warning_count is not None else 0
        strengths_count = int(strengths_count) if strengths_count is not None else 0
    except (ValueError, TypeError):
        critical_count = 0
        warning_count = 0
        strengths_count = 0
    
    if overall_status == 'pass':
        if strengths_count > 0:
            return f"Your documentation demonstrates good alignment with HCPC standards. You have {strengths_count} strength(s) identified. Continue to maintain these positive aspects in your record-keeping."
        else:
            return "Your documentation meets the basic requirements of HCPC standards. Consider reviewing the recommendations to further enhance your record-keeping."
    
    elif overall_status == 'needs_improvement':
        return f"Your documentation has {warning_count} area(s) that could be improved to better align with HCPC standards. Review the feedback below to identify specific enhancements you can make."
    
    elif overall_status == 'critical_issues':
        return f"Your documentation has {critical_count} critical issue(s) that should be addressed to meet HCPC standards. These are important for maintaining professional record-keeping standards. Please review the detailed feedback below."
    
    else:
        return "Review the feedback below to understand how your documentation aligns with HCPC standards."

def _generate_reflective_prompts(findings, strengths, overall_status):
    """Generate reflective prompts for continuous professional development"""
    prompts = []
    
    # General reflection prompt
    prompts.append({
        'type': 'general',
        'question': 'What aspects of your documentation do you feel are strongest?',
        'context': 'Reflecting on your strengths helps identify practices to maintain and build upon.'
    })
    
    # Category-specific prompts based on findings
    # Filter out None and non-string categories
    categories_with_issues = set(
        f.get('category') for f in findings 
        if f.get('category') and isinstance(f.get('category'), str)
    )
    
    if 'identification' in categories_with_issues:
        prompts.append({
            'type': 'identification',
            'question': 'How do you currently ensure all required identification elements are included in your notes?',
            'context': 'Consider your workflow for including date, time, and practitioner identifier.'
        })
    
    if 'structure' in categories_with_issues:
        prompts.append({
            'type': 'structure',
            'question': 'What structure or format do you find most helpful for organising your clinical notes?',
            'context': 'Reflect on how clear structure supports both your practice and continuity of care.'
        })
    
    if 'objectivity' in categories_with_issues:
        prompts.append({
            'type': 'objectivity',
            'question': 'How do you ensure your notes remain factual and objective?',
            'context': 'Consider strategies for maintaining professional tone while accurately documenting observations.'
        })
    
    if 'reasoning' in categories_with_issues:
        prompts.append({
            'type': 'reasoning',
            'question': 'How do you document the link between your findings and treatment decisions?',
            'context': 'Reflect on making your clinical reasoning transparent in your documentation.'
        })
    
    if 'plan' in categories_with_issues:
        prompts.append({
            'type': 'plan',
            'question': 'What information do you include in your treatment plans to support continuity of care?',
            'context': 'Consider what details help other practitioners understand your treatment approach.'
        })
    
    # Improvement-focused prompt
    if overall_status != 'pass':
        prompts.append({
            'type': 'improvement',
            'question': 'Which area would you like to focus on improving first?',
            'context': 'Prioritising improvements can help you make meaningful progress in your documentation.'
        })
    
    return prompts

def _generate_next_steps(findings, overall_status):
    """Generate actionable next steps based on findings"""
    next_steps = []
    
    # Prioritise critical issues
    critical_findings = [f for f in findings if f.get('severity') == 'critical']
    if critical_findings:
        # Filter out None and non-string categories
        critical_categories = list(set(
            f.get('category') for f in critical_findings 
            if f.get('category') and isinstance(f.get('category'), str)
        ))
        next_steps.append({
            'priority': 'high',
            'action': 'Address critical issues first',
            'description': f'Review and address the {len(critical_findings)} critical issue(s) identified in the feedback.',
            'categories': critical_categories
        })
    
    # Group by category for medium priority items
    categories_with_warnings = {}
    for finding in findings:
        if finding.get('severity') == 'warning':
            category_raw = finding.get('category')
            # Handle None, empty string, or non-string categories
            if not category_raw or not isinstance(category_raw, str):
                category = 'other'
            else:
                category = category_raw
            
            if category not in categories_with_warnings:
                categories_with_warnings[category] = []
            categories_with_warnings[category].append(finding)
    
    if categories_with_warnings:
        for category, category_findings in categories_with_warnings.items():
            # Safely convert category to title case
            category_title = category.title() if isinstance(category, str) else str(category).title()
            next_steps.append({
                'priority': 'medium',
                'action': f'Review {category_title} feedback',
                'description': f'Consider the {len(category_findings)} suggestion(s) for improving {category} in your documentation.',
                'categories': [category]
            })
    
    # General next step
    next_steps.append({
        'priority': 'low',
        'action': 'Review HCPC guidance',
        'description': 'Familiarise yourself with HCPC record-keeping standards to understand the regulatory basis for this feedback.',
        'categories': []
    })
    
    return next_steps

def lambda_handler(event, context):
    """
    Lambda handler for feedback generator
    
    Receives audit results and generates user-friendly feedback report
    Returns formatted feedback with strengths, findings, and recommendations
    """
    request_id = context.aws_request_id if context else 'unknown'
    
    try:
        # Validate event structure
        if not isinstance(event, dict):
            return error_response(400, 'Invalid request format', 'Event must be a dictionary', event, context)
        
        # Log request start
        logger.info(f"Feedback generation request started", extra={
            'request_id': request_id
        })
        
        # Parse request body with size limits
        body = {}
        if 'body' in event:
            body_content = event.get('body')
            
            # Security: Check body size before parsing (prevents DoS)
            if isinstance(body_content, str):
                body_size = len(body_content.encode('utf-8'))
                if body_size > MAX_BODY_SIZE:
                    return error_response(413, 'Request too large',
                                        f'Request body exceeds maximum size of {MAX_BODY_SIZE} bytes',
                                        event, context)
                body = json.loads(body_content)
            elif isinstance(event.get('body'), dict):
                # Estimate dict size for size check
                body_str = json.dumps(body_content)
                body_size = len(body_str.encode('utf-8'))
                if body_size > MAX_BODY_SIZE:
                    return error_response(413, 'Request too large',
                                        f'Request body exceeds maximum size of {MAX_BODY_SIZE} bytes',
                                        event, context)
                body = body_content
        
        if not isinstance(body, dict):
            body = {}
        
        # Get audit results from request
        audit_results = body.get('audit_results', {})
        
        # Validate audit results structure
        if not isinstance(audit_results, dict):
            return error_response(400, 'Invalid audit_results format',
                               'audit_results must be a dictionary',
                               event, context)
        
        # Validate required fields
        if 'overall_status' not in audit_results:
            return error_response(400, 'Missing required field',
                               'audit_results must include "overall_status" field',
                               event, context)
        
        # Generate feedback report
        try:
            feedback_report = generate_feedback_report(audit_results)
        except ValueError as e:
            # Input validation errors - return 400
            logger.warning(f"Invalid input in feedback generation: {e}", extra={
                'request_id': request_id,
                'error': str(e)
            })
            return error_response(400, 'Invalid input',
                                'Invalid audit results provided',
                                event, context)
        except Exception as e:
            # Other errors - sanitize message
            logger.error(f"Feedback generation failed: {e}", extra={
                'request_id': request_id,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return error_response(500, 'Feedback generation failed',
                                'An error occurred during feedback generation',
                                event, context)
        
        # Log successful generation
        logger.info(f"Feedback report generated successfully", extra={
            'request_id': request_id,
            'overall_status': feedback_report.get('overall_status'),
            'findings_count': feedback_report.get('summary', {}).get('total_findings', 0),
            'strengths_count': feedback_report.get('summary', {}).get('strengths_count', 0)
        })
        
        # Security: Check response size before returning (prevents Lambda timeout)
        response_body = json.dumps({
            'success': True,
            'message': 'Feedback report generated successfully',
            'data': feedback_report
        })
        
        response_size = len(response_body.encode('utf-8'))
        if response_size > MAX_RESPONSE_SIZE:
            logger.warning(f"Response size ({response_size}) exceeds maximum ({MAX_RESPONSE_SIZE}), truncating findings", extra={
                'request_id': request_id,
                'response_size': response_size
            })
            # Truncate findings if response is too large
            if 'findings' in feedback_report and len(feedback_report['findings']) > 100:
                feedback_report['findings'] = feedback_report['findings'][:100]
                feedback_report['summary']['total_findings'] = min(
                    feedback_report['summary'].get('total_findings', 0), 100
                )
                response_body = json.dumps({
                    'success': True,
                    'message': 'Feedback report generated successfully (truncated due to size)',
                    'data': feedback_report
                })
        
        # Return feedback report
        return {
            'statusCode': 200,
            'headers': get_cors_headers(event),
            'body': response_body
        }
        
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parsing error: {e}", extra={
            'request_id': request_id
        })
        return error_response(400, 'Invalid JSON in request body',
                            'Request body must be valid JSON',
                            event, context)
    
    except Exception as e:
        logger.error(f"Unexpected error in feedback handler: {e}", extra={
            'request_id': request_id,
            'error': str(e),
            'error_type': type(e).__name__
        })
        return error_response(500, 'Internal server error',
                            'An unexpected error occurred',
                            event, context)
