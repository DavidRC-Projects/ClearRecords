import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import json

# Add the function directory to the path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'document-processing'))

from app import lambda_handler, get_cors_origin, get_cors_headers, get_user_id, sanitize_error_message


class TestLambdaHandler(unittest.TestCase):
    """Unit tests for Lambda handler in app.py"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'REQUIRE_AUTH': 'true',
            'VALIDATE_USER_OWNERSHIP': 'true',
            'ALLOWED_ORIGINS': 'https://example.com,https://app.example.com',
            'S3_KEY_PREFIX': 'uploads/'
        })
        self.env_patcher.start()
        
        # Mock context
        self.context = Mock()
        self.context.aws_request_id = 'test-request-id-123'
        self.context.get_remaining_time_in_millis = Mock(return_value=30000)
        
        # Mock TextractProcessor
        self.processor_mock = Mock()
        self.processor_mock.process_document.return_value = {
            'success': True,
            'text': 'Sample extracted text',
            'tables': [{'id': 'table-1', 'rows': [['Header1', 'Header2']]}],
            'forms': [{'key': 'Field', 'value': 'Value'}]
        }
    
    def tearDown(self):
        """Clean up after each test method"""
        self.env_patcher.stop()
    
    def test_successful_document_processing(self):
        """Test successful document processing flow"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {
                'origin': 'https://example.com'
            }
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        self.assertIn('data', body)
        self.assertIn('text', body['data'])
        self.assertIn('tables', body['data'])
        self.assertIn('forms', body['data'])
    
    def test_missing_authentication(self):
        """Test that unauthenticated requests are rejected"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {},
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 401)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Unauthorized', body['error'])
    
    def test_authentication_disabled(self):
        """Test that authentication can be disabled via environment variable"""
        with patch.dict(os.environ, {'REQUIRE_AUTH': 'false'}):
            event = {
                'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
                'requestContext': {},
                'headers': {}
            }
            
            with patch('app.TextractProcessor', return_value=self.processor_mock):
                response = lambda_handler(event, self.context)
            
            # Should succeed without authentication
            self.assertEqual(response['statusCode'], 200)
    
    def test_missing_s3_key(self):
        """Test that missing s3_key parameter is rejected"""
        event = {
            'body': json.dumps({}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('s3_key', body['error'])
    
    def test_invalid_s3_key_type(self):
        """Test that non-string s3_key is rejected"""
        event = {
            'body': json.dumps({'s3_key': 12345}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_empty_s3_key(self):
        """Test that empty s3_key is rejected"""
        event = {
            'body': json.dumps({'s3_key': ''}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_s3_key_path_traversal_prevention(self):
        """Test that path traversal attempts are blocked"""
        event = {
            'body': json.dumps({'s3_key': '../../etc/passwd'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('path traversal', body['message'].lower())
    
    def test_s3_key_too_long(self):
        """Test that excessively long S3 keys are rejected"""
        long_key = 'a' * 2000  # Exceeds MAX_S3_KEY_LENGTH
        event = {
            'body': json.dumps({'s3_key': long_key}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_user_ownership_validation(self):
        """Test that users can only access their own documents"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/otheruser/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 403)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('Access denied', body['error'])
    
    def test_user_ownership_validation_disabled(self):
        """Test that ownership validation can be disabled"""
        with patch.dict(os.environ, {'VALIDATE_USER_OWNERSHIP': 'false'}):
            event = {
                'body': json.dumps({'s3_key': 'uploads/otheruser/document.pdf'}),
                'requestContext': {
                    'authorizer': {
                        'claims': {
                            'sub': 'user123'
                        }
                    }
                },
                'headers': {}
            }
            
            with patch('app.TextractProcessor', return_value=self.processor_mock):
                response = lambda_handler(event, self.context)
            
            # Should succeed when validation is disabled
            self.assertEqual(response['statusCode'], 200)
    
    def test_s3_key_prefix_validation(self):
        """Test that S3 key prefix validation works"""
        event = {
            'body': json.dumps({'s3_key': 'wrong-prefix/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 403)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_invalid_json_body(self):
        """Test handling of invalid JSON in request body"""
        event = {
            'body': 'invalid json {',
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('JSON', body['error'])
    
    def test_request_body_too_large(self):
        """Test that oversized request bodies are rejected"""
        large_body = 'x' * (11 * 1024)  # Exceeds MAX_BODY_SIZE
        event = {
            'body': large_body,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 413)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('too large', body['error'].lower())
    
    def test_textract_processor_failure(self):
        """Test handling of TextractProcessor failures"""
        self.processor_mock.process_document.return_value = {
            'success': False,
            'error': 'Document processing failed',
            'text': '',
            'tables': [],
            'forms': []
        }
        
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
        self.assertIn('processing failed', body['error'].lower())
    
    def test_textract_processor_initialization_failure(self):
        """Test handling of TextractProcessor initialization errors"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        with patch('app.TextractProcessor', side_effect=ValueError("Missing S3 bucket")):
            response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 500)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_invalid_event_structure(self):
        """Test handling of invalid event structure"""
        event = "not a dictionary"
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 400)
        body = json.loads(response['body'])
        self.assertFalse(body['success'])
    
    def test_cors_headers_included(self):
        """Test that CORS headers are included in responses"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {
                'origin': 'https://example.com'
            }
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertIn('X-Content-Type-Options', response['headers'])
        self.assertIn('X-Frame-Options', response['headers'])
    
    def test_cors_wildcard_origin_no_credentials(self):
        """Test that credentials are not set with wildcard origin"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'ALLOWED_ORIGINS': ''}):
            event = {
                'headers': {}
            }
            
            headers = get_cors_headers(event)
            
            # Should have wildcard origin but no credentials
            self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
            self.assertNotIn('Access-Control-Allow-Credentials', headers)
    
    def test_response_size_truncation(self):
        """Test that large responses are truncated"""
        # Create a very large text response
        large_text = 'x' * (7 * 1024 * 1024)  # 7MB text
        self.processor_mock.process_document.return_value = {
            'success': True,
            'text': large_text,
            'tables': [],
            'forms': []
        }
        
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertTrue(body['success'])
        # Text should be truncated
        self.assertIn('truncated', body['data']['text'].lower())
    
    def test_security_headers_present(self):
        """Test that all security headers are present"""
        event = {
            'body': json.dumps({'s3_key': 'uploads/user123/document.pdf'}),
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        headers = response['headers']
        self.assertIn('X-Content-Type-Options', headers)
        self.assertIn('X-Frame-Options', headers)
        self.assertIn('X-XSS-Protection', headers)
        self.assertIn('Strict-Transport-Security', headers)
        self.assertIn('Cache-Control', headers)
        self.assertIn('Pragma', headers)
    
    def test_dict_body_parsing(self):
        """Test that dict body (from API Gateway) is handled correctly"""
        event = {
            'body': {'s3_key': 'uploads/user123/document.pdf'},
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        with patch('app.TextractProcessor', return_value=self.processor_mock):
            response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 200)
    
    def test_dict_body_size_validation(self):
        """Test that dict body size is validated"""
        large_dict = {'s3_key': 'x' * (11 * 1024)}
        event = {
            'body': large_dict,
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            },
            'headers': {}
        }
        
        response = lambda_handler(event, self.context)
        
        self.assertEqual(response['statusCode'], 413)


class TestHelperFunctions(unittest.TestCase):
    """Unit tests for helper functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.env_patcher = patch.dict(os.environ, {
            'ALLOWED_ORIGINS': 'https://example.com, https://app.example.com',
            'ENVIRONMENT': 'production'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after each test"""
        self.env_patcher.stop()
    
    def test_get_cors_origin_allowed(self):
        """Test CORS origin validation with allowed origin"""
        event = {
            'headers': {
                'origin': 'https://example.com'
            }
        }
        
        origin = get_cors_origin(event)
        self.assertEqual(origin, 'https://example.com')
    
    def test_get_cors_origin_not_allowed(self):
        """Test CORS origin validation with disallowed origin"""
        event = {
            'headers': {
                'origin': 'https://evil.com'
            }
        }
        
        origin = get_cors_origin(event)
        self.assertEqual(origin, 'null')
    
    def test_get_cors_origin_whitespace_handling(self):
        """Test that whitespace in ALLOWED_ORIGINS is handled"""
        with patch.dict(os.environ, {'ALLOWED_ORIGINS': ' https://example.com , https://app.example.com '}):
            event = {
                'headers': {
                    'origin': 'https://example.com'
                }
            }
            
            origin = get_cors_origin(event)
            self.assertEqual(origin, 'https://example.com')
    
    def test_get_cors_origin_development_mode(self):
        """Test CORS in development mode"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'ALLOWED_ORIGINS': ''}):
            event = {
                'headers': {}
            }
            
            origin = get_cors_origin(event)
            self.assertEqual(origin, '*')
    
    def test_get_cors_headers_with_credentials(self):
        """Test CORS headers with credentials for specific origin"""
        event = {
            'headers': {
                'origin': 'https://example.com'
            }
        }
        
        headers = get_cors_headers(event)
        self.assertEqual(headers['Access-Control-Allow-Origin'], 'https://example.com')
        self.assertEqual(headers['Access-Control-Allow-Credentials'], 'true')
    
    def test_get_cors_headers_no_credentials_with_wildcard(self):
        """Test that credentials are not set with wildcard"""
        with patch.dict(os.environ, {'ENVIRONMENT': 'development', 'ALLOWED_ORIGINS': ''}):
            event = {
                'headers': {}
            }
            
            headers = get_cors_headers(event)
            self.assertEqual(headers['Access-Control-Allow-Origin'], '*')
            self.assertNotIn('Access-Control-Allow-Credentials', headers)
    
    def test_get_user_id_from_claims(self):
        """Test extracting user ID from Cognito claims"""
        event = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': 'user123'
                    }
                }
            }
        }
        
        user_id = get_user_id(event)
        self.assertEqual(user_id, 'user123')
    
    def test_get_user_id_anonymous(self):
        """Test that anonymous user ID is returned when no auth"""
        event = {
            'requestContext': {}
        }
        
        user_id = get_user_id(event)
        self.assertEqual(user_id, 'anonymous')
    
    def test_sanitize_error_message_production(self):
        """Test error message sanitization in production"""
        error_msg = "AccessDenied: User arn:aws:iam::123456789:user/test cannot access s3://bucket/key"
        sanitized = sanitize_error_message(error_msg, is_dev=False)
        
        self.assertNotIn('arn:aws', sanitized)
        self.assertNotIn('123456789', sanitized)
        self.assertIn('failed', sanitized.lower())
    
    def test_sanitize_error_message_development(self):
        """Test that error messages are not sanitized in development"""
        error_msg = "AccessDenied: User cannot access"
        sanitized = sanitize_error_message(error_msg, is_dev=True)
        
        self.assertEqual(sanitized, error_msg)


if __name__ == '__main__':
    unittest.main()
