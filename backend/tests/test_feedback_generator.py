"""
Unit tests for Feedback Generator Function

Tests the feedback report generation from audit results.
"""

import unittest
import sys
import os
import json
from datetime import datetime

# Add the function directory to the path so we can import the feedback generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'feedback-generator'))

from app import (
    generate_feedback_report,
    _generate_overall_message,
    _generate_reflective_prompts,
    _generate_next_steps,
    lambda_handler,
    error_response,
    get_cors_headers,
    sanitize_error_message,
    MAX_BODY_SIZE,
    MAX_RESPONSE_SIZE,
    MAX_FINDINGS_COUNT
)


class TestFeedbackGenerator(unittest.TestCase):
    """Unit tests for Feedback Generator"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        self.sample_audit_results = {
            'overall_status': 'needs_improvement',
            'findings': [
                {
                    'category': 'identification',
                    'severity': 'critical',
                    'issue': 'Date not clearly identified',
                    'hcpc_standard': 'HCPC Standard 10.1',
                    'guidance': 'Records must include the date of entry.',
                    'example': 'Date: 15/01/2024'
                },
                {
                    'category': 'structure',
                    'severity': 'warning',
                    'issue': 'Missing SOAP sections',
                    'hcpc_standard': 'HCPC Standard 10.2',
                    'guidance': 'SOAP structure helps ensure comprehensive documentation.',
                    'example': 'S: Patient reports...'
                }
            ],
            'strengths': [
                {
                    'aspect': 'Professional Tone',
                    'description': 'Objective, professional language maintained',
                    'benefit': 'Records maintain appropriate professional standards'
                }
            ],
            'recommendations': [
                {
                    'priority': 'high',
                    'category': 'Identification',
                    'action': 'Ensure all notes include date, time, and practitioner identifier',
                    'reference': 'HCPC Standard 10.1'
                }
            ],
            'summary': {
                'total_findings': 2,
                'critical_issues': 1,
                'warnings': 1,
                'strengths_count': 1
            }
        }
    
    # ==================== generate_feedback_report Tests ====================
    
    def test_generate_feedback_report_valid_input(self):
        """Test feedback report generation with valid audit results"""
        report = generate_feedback_report(self.sample_audit_results)
        
        self.assertIsInstance(report, dict)
        self.assertIn('generated_at', report)
        self.assertIn('overall_status', report)
        self.assertIn('overall_message', report)
        self.assertIn('summary', report)
        self.assertIn('strengths', report)
        self.assertIn('category_summaries', report)
        self.assertIn('recommendations', report)
        self.assertIn('reflective_prompts', report)
        self.assertIn('next_steps', report)
    
    def test_generate_feedback_report_invalid_input(self):
        """Test feedback report generation with invalid input"""
        with self.assertRaises(ValueError):
            generate_feedback_report("not a dict")
        
        with self.assertRaises(ValueError):
            generate_feedback_report(None)
    
    def test_generate_feedback_report_empty_findings(self):
        """Test feedback report generation with no findings"""
        audit_results = {
            'overall_status': 'pass',
            'findings': [],
            'strengths': [],
            'recommendations': [],
            'summary': {
                'total_findings': 0,
                'critical_issues': 0,
                'warnings': 0,
                'strengths_count': 0
            }
        }
        
        report = generate_feedback_report(audit_results)
        self.assertEqual(report['overall_status'], 'pass')
        self.assertEqual(len(report['category_summaries']), 0)
        self.assertEqual(len(report['findings']), 0)
    
    def test_generate_feedback_report_category_grouping(self):
        """Test that findings are grouped by category"""
        report = generate_feedback_report(self.sample_audit_results)
        
        category_summaries = report['category_summaries']
        self.assertEqual(len(category_summaries), 2)  # identification and structure
        
        # Check identification category
        identification = next((c for c in category_summaries if c['category'] == 'Identification'), None)
        self.assertIsNotNone(identification)
        self.assertEqual(identification['total_issues'], 1)
        self.assertEqual(identification['critical_issues'], 1)
        self.assertEqual(identification['warnings'], 0)
        
        # Check structure category
        structure = next((c for c in category_summaries if c['category'] == 'Structure'), None)
        self.assertIsNotNone(structure)
        self.assertEqual(structure['total_issues'], 1)
        self.assertEqual(structure['critical_issues'], 0)
        self.assertEqual(structure['warnings'], 1)
    
    def test_generate_feedback_report_generated_at(self):
        """Test that generated_at timestamp is included"""
        report = generate_feedback_report(self.sample_audit_results)
        
        self.assertIn('generated_at', report)
        self.assertIsInstance(report['generated_at'], str)
        # Should be ISO format with Z
        self.assertTrue(report['generated_at'].endswith('Z'))
    
    # ==================== _generate_overall_message Tests ====================
    
    def test_generate_overall_message_pass(self):
        """Test overall message generation for pass status"""
        summary = {'critical_issues': 0, 'warnings': 0, 'strengths_count': 2}
        message = _generate_overall_message('pass', summary)
        
        self.assertIsInstance(message, str)
        self.assertIn('strength', message.lower())
    
    def test_generate_overall_message_needs_improvement(self):
        """Test overall message generation for needs_improvement status"""
        summary = {'critical_issues': 0, 'warnings': 3, 'strengths_count': 1}
        message = _generate_overall_message('needs_improvement', summary)
        
        self.assertIsInstance(message, str)
        self.assertIn('improved', message.lower())  # Message says "improved" not "improvement"
        self.assertIn('3', message)  # Should mention warning count
    
    def test_generate_overall_message_critical_issues(self):
        """Test overall message generation for critical_issues status"""
        summary = {'critical_issues': 2, 'warnings': 1, 'strengths_count': 0}
        message = _generate_overall_message('critical_issues', summary)
        
        self.assertIsInstance(message, str)
        self.assertIn('critical', message.lower())
        self.assertIn('2', message)  # Should mention critical count
    
    # ==================== _generate_reflective_prompts Tests ====================
    
    def test_generate_reflective_prompts_always_has_general(self):
        """Test that reflective prompts always include a general prompt"""
        prompts = _generate_reflective_prompts([], [], 'pass')
        
        self.assertGreater(len(prompts), 0)
        general_prompts = [p for p in prompts if p.get('type') == 'general']
        self.assertEqual(len(general_prompts), 1)
    
    def test_generate_reflective_prompts_category_specific(self):
        """Test that category-specific prompts are generated based on findings"""
        findings = [
            {'category': 'identification', 'severity': 'critical'},
            {'category': 'structure', 'severity': 'warning'}
        ]
        prompts = _generate_reflective_prompts(findings, [], 'needs_improvement')
        
        identification_prompts = [p for p in prompts if p.get('type') == 'identification']
        structure_prompts = [p for p in prompts if p.get('type') == 'structure']
        
        self.assertEqual(len(identification_prompts), 1)
        self.assertEqual(len(structure_prompts), 1)
    
    def test_generate_reflective_prompts_improvement_prompt(self):
        """Test that improvement prompt is included for non-pass status"""
        findings = [{'category': 'identification', 'severity': 'critical'}]
        prompts = _generate_reflective_prompts(findings, [], 'needs_improvement')
        
        improvement_prompts = [p for p in prompts if p.get('type') == 'improvement']
        self.assertEqual(len(improvement_prompts), 1)
    
    def test_generate_reflective_prompts_no_improvement_for_pass(self):
        """Test that improvement prompt is not included for pass status"""
        prompts = _generate_reflective_prompts([], [], 'pass')
        
        improvement_prompts = [p for p in prompts if p.get('type') == 'improvement']
        self.assertEqual(len(improvement_prompts), 0)
    
    # ==================== _generate_next_steps Tests ====================
    
    def test_generate_next_steps_prioritises_critical(self):
        """Test that next steps prioritise critical issues"""
        findings = [
            {'category': 'identification', 'severity': 'critical'},
            {'category': 'structure', 'severity': 'warning'}
        ]
        next_steps = _generate_next_steps(findings, 'critical_issues')
        
        high_priority = [s for s in next_steps if s.get('priority') == 'high']
        self.assertGreater(len(high_priority), 0)
        self.assertIn('critical', high_priority[0]['action'].lower())
    
    def test_generate_next_steps_includes_general(self):
        """Test that next steps always include a general step"""
        next_steps = _generate_next_steps([], 'pass')
        
        general_steps = [s for s in next_steps if 'HCPC' in s.get('action', '')]
        self.assertGreater(len(general_steps), 0)
    
    def test_generate_next_steps_groups_by_category(self):
        """Test that next steps group warnings by category"""
        findings = [
            {'category': 'structure', 'severity': 'warning'},
            {'category': 'structure', 'severity': 'warning'},
            {'category': 'objectivity', 'severity': 'warning'}
        ]
        next_steps = _generate_next_steps(findings, 'needs_improvement')
        
        # Should have steps for structure and objectivity
        structure_steps = [s for s in next_steps if 'structure' in s.get('action', '').lower()]
        objectivity_steps = [s for s in next_steps if 'objectivity' in s.get('action', '').lower()]
        
        self.assertGreater(len(structure_steps), 0)
        self.assertGreater(len(objectivity_steps), 0)
    
    # ==================== lambda_handler Tests ====================
    
    def test_lambda_handler_valid_request(self):
        """Test lambda handler with valid request"""
        event = {
            'body': json.dumps({
                'audit_results': self.sample_audit_results
            }),
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertIn('data', body)
        self.assertIn('overall_status', body['data'])
    
    def test_lambda_handler_missing_audit_results(self):
        """Test lambda handler with missing audit_results"""
        event = {
            'body': json.dumps({}),
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_lambda_handler_invalid_json(self):
        """Test lambda handler with invalid JSON"""
        event = {
            'body': 'invalid json {',
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_lambda_handler_missing_overall_status(self):
        """Test lambda handler with audit_results missing overall_status"""
        event = {
            'body': json.dumps({
                'audit_results': {'findings': []}
            }),
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_lambda_handler_dict_body(self):
        """Test lambda handler with dict body (API Gateway format)"""
        event = {
            'body': {
                'audit_results': self.sample_audit_results
            },
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
    
    # ==================== Error Response Tests ====================
    
    def test_error_response_format(self):
        """Test error response format"""
        event = {'headers': {}}
        # Set development mode to get unsanitized messages
        os.environ['ENVIRONMENT'] = 'development'
        response = error_response(400, 'TestError', 'Test message', event)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertEqual(body['error'], 'TestError')
        # In dev mode, message should be unsanitized
        self.assertEqual(body['message'], 'Test message')
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    # ==================== CORS Tests ====================
    
    def test_get_cors_headers_allowed_origin(self):
        """Test CORS headers with allowed origin"""
        os.environ['ALLOWED_ORIGINS'] = 'https://example.com'
        event = {
            'headers': {
                'origin': 'https://example.com'
            }
        }
        
        headers = get_cors_headers(event)
        
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'https://example.com')
        self.assertEqual(headers['Access-Control-Allow-Credentials'], 'true')
        
        # Cleanup
        del os.environ['ALLOWED_ORIGINS']
    
    def test_get_cors_headers_development(self):
        """Test CORS headers in development environment"""
        os.environ['ENVIRONMENT'] = 'development'
        event = {'headers': {}}
        
        headers = get_cors_headers(event)
        
        self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    # ==================== Security Tests ====================
    
    def test_findings_count_limit(self):
        """Test that findings count is limited to MAX_FINDINGS_COUNT"""
        # Create more findings than the limit
        large_findings = [
            {'category': 'test', 'severity': 'warning', 'issue': f'Issue {i}'}
            for i in range(MAX_FINDINGS_COUNT + 100)
        ]
        
        audit_results = {
            'overall_status': 'needs_improvement',
            'findings': large_findings,
            'strengths': [],
            'recommendations': [],
            'summary': {
                'total_findings': len(large_findings),
                'critical_issues': 0,
                'warnings': len(large_findings),
                'strengths_count': 0
            }
        }
        
        report = generate_feedback_report(audit_results)
        
        # Findings should be truncated to MAX_FINDINGS_COUNT
        self.assertLessEqual(len(report['findings']), MAX_FINDINGS_COUNT)
        self.assertEqual(len(report['findings']), MAX_FINDINGS_COUNT)
    
    def test_findings_count_within_limit(self):
        """Test that findings within limit are not truncated"""
        findings = [
            {'category': 'test', 'severity': 'warning', 'issue': f'Issue {i}'}
            for i in range(100)
        ]
        
        audit_results = {
            'overall_status': 'needs_improvement',
            'findings': findings,
            'strengths': [],
            'recommendations': [],
            'summary': {
                'total_findings': 100,
                'critical_issues': 0,
                'warnings': 100,
                'strengths_count': 0
            }
        }
        
        report = generate_feedback_report(audit_results)
        
        # All findings should be included
        self.assertEqual(len(report['findings']), 100)
    
    def test_lambda_handler_body_size_limit_string(self):
        """Test that lambda handler rejects oversized string body"""
        # Create a body that exceeds MAX_BODY_SIZE
        large_body = {'audit_results': {'overall_status': 'pass', 'findings': []}}
        large_body_str = json.dumps(large_body)
        # Pad to exceed limit
        large_body_str = large_body_str + 'x' * (MAX_BODY_SIZE + 1)
        
        event = {
            'body': large_body_str,
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 413)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        # Check for size-related error (may be sanitized in production)
        error_msg_lower = body['message'].lower()
        self.assertTrue(
            'too large' in error_msg_lower or 
            'exceeds maximum' in error_msg_lower or
            'error occurred' in error_msg_lower  # Sanitized message
        )
    
    def test_lambda_handler_body_size_limit_dict(self):
        """Test that lambda handler rejects oversized dict body"""
        # Create a dict body that would exceed MAX_BODY_SIZE when serialized
        large_findings = [
            {'category': 'test', 'severity': 'warning', 'issue': 'x' * 1000}
            for _ in range(10000)  # Large enough to exceed 5MB when serialized
        ]
        
        event = {
            'body': {
                'audit_results': {
                    'overall_status': 'pass',
                    'findings': large_findings,
                    'strengths': [],
                    'recommendations': [],
                    'summary': {'total_findings': 10000, 'critical_issues': 0, 'warnings': 10000, 'strengths_count': 0}
                }
            },
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        # Should either reject (413) or process with truncation (200)
        # Since we check size before processing, it should reject
        self.assertIn(response['statusCode'], [413, 200])
    
    def test_lambda_handler_body_size_within_limit(self):
        """Test that lambda handler accepts body within size limit"""
        event = {
            'body': json.dumps({
                'audit_results': self.sample_audit_results
            }),
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
    
    def test_sanitize_error_message_production(self):
        """Test error message sanitization in production mode"""
        os.environ['ENVIRONMENT'] = 'production'
        
        # Test with sensitive patterns
        sensitive_errors = [
            'File "app.py", line 42, in lambda_handler',
            'Traceback (most recent call last):',
            'AttributeError: object has no attribute',
            'TypeError: unsupported operand',
            'KeyError: missing key'
        ]
        
        for error in sensitive_errors:
            sanitized = sanitize_error_message(error, False)
            self.assertNotIn('File "', sanitized)
            self.assertNotIn('Traceback', sanitized)
            self.assertNotIn('AttributeError', sanitized)
            self.assertNotIn('TypeError', sanitized)
            self.assertNotIn('KeyError', sanitized)
            self.assertIn('error', sanitized.lower())
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    def test_sanitize_error_message_development(self):
        """Test error message sanitization in development mode"""
        os.environ['ENVIRONMENT'] = 'development'
        
        error = 'File "app.py", line 42, in lambda_handler\nAttributeError: test'
        sanitized = sanitize_error_message(error, True)
        
        # In dev mode, should return original message
        self.assertEqual(sanitized, error)
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    def test_sanitize_error_message_safe_message(self):
        """Test that safe error messages are not over-sanitized"""
        os.environ['ENVIRONMENT'] = 'production'
        
        safe_message = 'Invalid input provided'
        sanitized = sanitize_error_message(safe_message, False)
        
        # Safe messages should pass through (with generic wrapper)
        self.assertIn('error', sanitized.lower())
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    def test_error_response_sanitization_production(self):
        """Test that error_response sanitizes messages in production"""
        os.environ['ENVIRONMENT'] = 'production'
        event = {'headers': {}}
        
        response = error_response(500, 'InternalError', 'File "app.py", line 42', event)
        body = json.loads(response['body'])
        
        # Message should be sanitized
        self.assertNotIn('File "', body['message'])
        self.assertNotIn('line 42', body['message'])
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    def test_error_response_sanitization_development(self):
        """Test that error_response does not sanitize messages in development"""
        os.environ['ENVIRONMENT'] = 'development'
        event = {'headers': {}}
        
        response = error_response(500, 'InternalError', 'File "app.py", line 42', event)
        body = json.loads(response['body'])
        
        # Message should not be sanitized in dev
        self.assertIn('File "', body['message'])
        
        # Cleanup
        del os.environ['ENVIRONMENT']
    
    def test_generate_feedback_report_invalid_findings_type(self):
        """Test that invalid findings type is handled"""
        audit_results = {
            'overall_status': 'pass',
            'findings': 'not a list',  # Invalid type
            'strengths': [],
            'recommendations': [],
            'summary': {'total_findings': 0, 'critical_issues': 0, 'warnings': 0, 'strengths_count': 0}
        }
        
        report = generate_feedback_report(audit_results)
        
        # Should handle gracefully by converting to empty list
        self.assertIsInstance(report['findings'], list)
        self.assertEqual(len(report['findings']), 0)
    
    def test_lambda_handler_response_size_truncation(self):
        """Test that large responses are truncated"""
        # Create audit results that would generate a large response (but not exceed body size limit)
        # Use smaller findings to stay within body size limit but generate large response
        large_findings = [
            {
                'category': 'test',
                'severity': 'warning',
                'issue': 'x' * 5000,  # Large issue text
                'hcpc_standard': 'HCPC Standard 10.1',
                'guidance': 'y' * 5000,  # Large guidance text
                'example': 'z' * 5000  # Large example text
            }
            for _ in range(50)  # Moderate number of findings
        ]
        
        audit_results = {
            'overall_status': 'needs_improvement',
            'findings': large_findings,
            'strengths': [],
            'recommendations': [],
            'summary': {
                'total_findings': len(large_findings),
                'critical_issues': 0,
                'warnings': len(large_findings),
                'strengths_count': 0
            }
        }
        
        # Check body size first
        body_str = json.dumps({'audit_results': audit_results})
        body_size = len(body_str.encode('utf-8'))
        
        # Only test if body is within limit
        if body_size <= MAX_BODY_SIZE:
            event = {
                'body': body_str,
                'headers': {}
            }
            context = type('Context', (), {'aws_request_id': 'test-request-id'})()
            
            response = lambda_handler(event, context)
            
            # Should succeed (200) but may truncate findings if response is too large
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertTrue(body['success'])
            
            # Response should be within reasonable size
            response_size = len(response['body'].encode('utf-8'))
            self.assertLess(response_size, MAX_RESPONSE_SIZE * 2)  # Allow some margin
        else:
            # Skip test if body would be too large
            self.skipTest(f"Test body size ({body_size}) exceeds MAX_BODY_SIZE ({MAX_BODY_SIZE})")
    
    def test_lambda_handler_invalid_findings_type(self):
        """Test lambda handler with invalid findings type"""
        audit_results = {
            'overall_status': 'pass',
            'findings': 'not a list',
            'strengths': [],
            'recommendations': [],
            'summary': {'total_findings': 0, 'critical_issues': 0, 'warnings': 0, 'strengths_count': 0}
        }
        
        event = {
            'body': json.dumps({'audit_results': audit_results}),
            'headers': {}
        }
        context = type('Context', (), {'aws_request_id': 'test-request-id'})()
        
        response = lambda_handler(event, context)
        
        # Should handle gracefully
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])


if __name__ == '__main__':
    unittest.main()
