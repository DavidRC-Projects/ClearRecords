import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the function directory to the path so we can import the processor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'functions', 'document-processing'))

from texttract_processor import TextractProcessor


class TestTextractProcessor(unittest.TestCase):
    """Unit tests for TextractProcessor class"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'AWS_REGION': 'eu-west-2',
            'S3_TEMP_BUCKET': 'test-bucket',
            'TEXTRACT_ROLE_ARN': 'arn:aws:iam::123456789:role/TestRole'
        })
        self.env_patcher.start()
        
        # Mock boto3 clients
        self.textract_mock = Mock()
        self.s3_mock = Mock()
        
        with patch('boto3.client') as mock_client:
            def client_side_effect(service_name, **kwargs):
                if service_name == 'textract':
                    return self.textract_mock
                elif service_name == 's3':
                    return self.s3_mock
                return Mock()
            
            mock_client.side_effect = client_side_effect
            self.processor = TextractProcessor()
    
    def tearDown(self):
        """Clean up after each test method"""
        self.env_patcher.stop()
    
    def test_init(self):
        """Test that TextractProcessor initializes correctly"""
        self.assertEqual(self.processor.s3_bucket, 'test-bucket')
        self.assertEqual(self.processor.role_arn, 'arn:aws:iam::123456789:role/TestRole')
        self.assertIsNotNone(self.processor.textract)
        self.assertIsNotNone(self.processor.s3_client)
    
    def test_process_document_success_simple_text(self):
        """Test successful document processing with simple text"""
        # Mock Textract response with simple text
        mock_response = {
            'Blocks': [
                {
                    'Id': 'line-1',
                    'BlockType': 'LINE',
                    'Text': 'Patient presents with lower back pain'
                },
                {
                    'Id': 'line-2',
                    'BlockType': 'LINE',
                    'Text': 'Assessment: Musculoskeletal issue'
                }
            ]
        }
        
        self.textract_mock.analyze_document.return_value = mock_response
        
        result = self.processor.process_document('test-document.jpg')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertIn('text', result)
        self.assertIn('tables', result)
        self.assertIn('forms', result)
        self.assertEqual(len(result['tables']), 0)  # No tables in this response
        self.assertEqual(len(result['forms']), 0)  # No forms in this response
        self.assertIn('Patient presents', result['text'])
        self.assertIn('Assessment', result['text'])
        self.assertIn('blocks', result)
    
    def test_process_document_with_tables(self):
        """Test document processing with table extraction"""
        # Create a realistic Textract response with a table
        mock_response = {
            'Blocks': [
                # Table block
                {
                    'Id': 'table-1',
                    'BlockType': 'TABLE',
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['cell-1', 'cell-2', 'cell-3', 'cell-4']
                        }
                    ]
                },
                # Cell blocks
                {
                    'Id': 'cell-1',
                    'BlockType': 'CELL',
                    'RowIndex': 1,
                    'ColumnIndex': 1,
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-1']
                        }
                    ]
                },
                {
                    'Id': 'cell-2',
                    'BlockType': 'CELL',
                    'RowIndex': 1,
                    'ColumnIndex': 2,
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-2']
                        }
                    ]
                },
                {
                    'Id': 'cell-3',
                    'BlockType': 'CELL',
                    'RowIndex': 2,
                    'ColumnIndex': 1,
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-3']
                        }
                    ]
                },
                {
                    'Id': 'cell-4',
                    'BlockType': 'CELL',
                    'RowIndex': 2,
                    'ColumnIndex': 2,
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-4']
                        }
                    ]
                },
                # Word blocks
                {
                    'Id': 'word-1',
                    'BlockType': 'WORD',
                    'Text': 'Date'
                },
                {
                    'Id': 'word-2',
                    'BlockType': 'WORD',
                    'Text': 'Time'
                },
                {
                    'Id': 'word-3',
                    'BlockType': 'WORD',
                    'Text': '2024-01-15'
                },
                {
                    'Id': 'word-4',
                    'BlockType': 'WORD',
                    'Text': '10:30'
                },
                # Line blocks
                {
                    'Id': 'line-1',
                    'BlockType': 'LINE',
                    'Text': 'Appointment Schedule'
                }
            ]
        }
        
        self.textract_mock.analyze_document.return_value = mock_response
        
        result = self.processor.process_document('test-table.jpg')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(len(result['tables']), 1)
        self.assertEqual(len(result['tables'][0]['rows']), 2)
        self.assertEqual(result['tables'][0]['rows'][0], ['Date', 'Time'])
        self.assertEqual(result['tables'][0]['rows'][1], ['2024-01-15', '10:30'])
        self.assertEqual(result['tables'][0]['id'], 'table-1')
    
    def test_process_document_with_forms(self):
        """Test document processing with form key-value extraction"""
        mock_response = {
            'Blocks': [
                # Key block
                {
                    'Id': 'key-1',
                    'BlockType': 'KEY_VALUE_SET',
                    'EntityTypes': ['KEY'],
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-1', 'word-2']
                        },
                        {
                            'Type': 'VALUE',
                            'Ids': ['value-1']
                        }
                    ]
                },
                # Value block
                {
                    'Id': 'value-1',
                    'BlockType': 'KEY_VALUE_SET',
                    'EntityTypes': ['VALUE'],
                    'Relationships': [
                        {
                            'Type': 'CHILD',
                            'Ids': ['word-3']
                        }
                    ]
                },
                # Word blocks
                {
                    'Id': 'word-1',
                    'BlockType': 'WORD',
                    'Text': 'Patient'
                },
                {
                    'Id': 'word-2',
                    'BlockType': 'WORD',
                    'Text': 'ID'
                },
                {
                    'Id': 'word-3',
                    'BlockType': 'WORD',
                    'Text': 'PT-12345'
                }
            ]
        }
        
        self.textract_mock.analyze_document.return_value = mock_response
        
        result = self.processor.process_document('test-form.jpg')
        
        # Assertions
        self.assertTrue(result['success'])
        self.assertEqual(len(result['forms']), 1)
        self.assertEqual(result['forms'][0]['key'], 'Patient ID')
        self.assertEqual(result['forms'][0]['value'], 'PT-12345')
    
    def test_process_document_error_handling(self):
        """Test error handling when Textract fails"""
        # Mock Textract to raise an exception
        self.textract_mock.analyze_document.side_effect = Exception('Textract service error')
        
        result = self.processor.process_document('test-document.jpg')
        
        # Assertions
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertEqual(result['text'], '')
        self.assertEqual(result['tables'], [])
        self.assertEqual(result['forms'], [])
    
    def test_extract_text_data(self):
        """Test text data extraction from Textract response"""
        mock_response = {
            'Blocks': [
                {
                    'Id': 'line-1',
                    'BlockType': 'LINE',
                    'Text': 'First line of text'
                },
                {
                    'Id': 'line-2',
                    'BlockType': 'LINE',
                    'Text': 'Second line of text'
                },
                {
                    'Id': 'word-1',
                    'BlockType': 'WORD',
                    'Text': 'Some'
                }
            ]
        }
        
        result = self.processor._extract_text_data(mock_response)
        
        # Assertions
        self.assertIn('full_text', result)
        self.assertIn('tables', result)
        self.assertIn('forms', result)
        self.assertIn('First line of text', result['full_text'])
        self.assertIn('Second line of text', result['full_text'])
        self.assertEqual(result['full_text'], 'First line of text\nSecond line of text')
    
    def test_extract_tables_empty(self):
        """Test table extraction with no tables"""
        blocks = [
            {
                'Id': 'line-1',
                'BlockType': 'LINE',
                'Text': 'Just some text'
            }
        ]
        block_map = {block['Id']: block for block in blocks}
        
        result = self.processor._extract_tables(blocks, block_map)
        
        self.assertEqual(result, [])
    
    def test_extract_forms_empty(self):
        """Test form extraction with no forms"""
        blocks = [
            {
                'Id': 'line-1',
                'BlockType': 'LINE',
                'Text': 'Just some text'
            }
        ]
        block_map = {block['Id']: block for block in blocks}
        
        result = self.processor._extract_forms(blocks, block_map)
        
        self.assertEqual(result, [])
    
    def test_extract_tables_complex(self):
        """Test extraction of a more complex table structure"""
        blocks = [
            {
                'Id': 'table-1',
                'BlockType': 'TABLE',
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['cell-1', 'cell-2', 'cell-3']
                    }
                ]
            },
            {
                'Id': 'cell-1',
                'BlockType': 'CELL',
                'RowIndex': 1,
                'ColumnIndex': 1,
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-1', 'word-2']
                    }
                ]
            },
            {
                'Id': 'cell-2',
                'BlockType': 'CELL',
                'RowIndex': 1,
                'ColumnIndex': 2,
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-3']
                    }
                ]
            },
            {
                'Id': 'cell-3',
                'BlockType': 'CELL',
                'RowIndex': 2,
                'ColumnIndex': 1,
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-4']
                    }
                ]
            },
            {
                'Id': 'word-1',
                'BlockType': 'WORD',
                'Text': 'Exercise'
            },
            {
                'Id': 'word-2',
                'BlockType': 'WORD',
                'Text': 'Type'
            },
            {
                'Id': 'word-3',
                'BlockType': 'WORD',
                'Text': 'Reps'
            },
            {
                'Id': 'word-4',
                'BlockType': 'WORD',
                'Text': 'Squats'
            }
        ]
        block_map = {block['Id']: block for block in blocks}
        
        result = self.processor._extract_tables(blocks, block_map)
        
        # Assertions
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]['rows']), 2)
        self.assertEqual(result[0]['rows'][0], ['Exercise Type', 'Reps'])
        self.assertEqual(result[0]['rows'][1], ['Squats'])
    
    def test_extract_forms_multiple(self):
        """Test extraction of multiple form key-value pairs"""
        blocks = [
            {
                'Id': 'key-1',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['KEY'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-1']
                    },
                    {
                        'Type': 'VALUE',
                        'Ids': ['value-1']
                    }
                ]
            },
            {
                'Id': 'key-2',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['KEY'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-3']
                    },
                    {
                        'Type': 'VALUE',
                        'Ids': ['value-2']
                    }
                ]
            },
            {
                'Id': 'value-1',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['VALUE'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-2']
                    }
                ]
            },
            {
                'Id': 'value-2',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['VALUE'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-4']
                    }
                ]
            },
            {
                'Id': 'word-1',
                'BlockType': 'WORD',
                'Text': 'Name'
            },
            {
                'Id': 'word-2',
                'BlockType': 'WORD',
                'Text': 'John'
            },
            {
                'Id': 'word-3',
                'BlockType': 'WORD',
                'Text': 'Age'
            },
            {
                'Id': 'word-4',
                'BlockType': 'WORD',
                'Text': '30'
            }
        ]
        block_map = {block['Id']: block for block in blocks}
        
        result = self.processor._extract_forms(blocks, block_map)
        
        # Assertions
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['key'], 'Name')
        self.assertEqual(result[0]['value'], 'John')
        self.assertEqual(result[1]['key'], 'Age')
        self.assertEqual(result[1]['value'], '30')
    
    def test_extract_forms_empty_key(self):
        """Test that forms with empty keys are not included"""
        blocks = [
            {
                'Id': 'key-1',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['KEY'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': []  # No words, so key will be empty
                    },
                    {
                        'Type': 'VALUE',
                        'Ids': ['value-1']
                    }
                ]
            },
            {
                'Id': 'value-1',
                'BlockType': 'KEY_VALUE_SET',
                'EntityTypes': ['VALUE'],
                'Relationships': [
                    {
                        'Type': 'CHILD',
                        'Ids': ['word-1']
                    }
                ]
            },
            {
                'Id': 'word-1',
                'BlockType': 'WORD',
                'Text': 'Some value'
            }
        ]
        block_map = {block['Id']: block for block in blocks}
        
        result = self.processor._extract_forms(blocks, block_map)
        
        # Assertions - empty key should not be included
        self.assertEqual(len(result), 0)
    
    def test_process_document_calls_textract_correctly(self):
        """Test that process_document calls Textract with correct parameters"""
        mock_response = {'Blocks': []}
        self.textract_mock.analyze_document.return_value = mock_response
        
        self.processor.process_document('test-doc.jpg')
        
        # Verify Textract was called with correct parameters
        self.textract_mock.analyze_document.assert_called_once()
        call_args = self.textract_mock.analyze_document.call_args
        
        self.assertEqual(call_args[1]['FeatureTypes'], ['TABLES', 'FORMS'])
        self.assertEqual(call_args[1]['Document']['S3Object']['Bucket'], 'test-bucket')
        self.assertEqual(call_args[1]['Document']['S3Object']['Name'], 'test-doc.jpg')


if __name__ == '__main__':
    unittest.main()
