import boto3
import os
import re
import time
import random
from botocore.exceptions import ClientError

class TextractProcessor:
    """
    Handles AWS Textract document processing
    Extracts text and structured data from images
    """
    
    def __init__(self):
        """Initialise Textract client with security validation"""
        # Validate and set S3 bucket
        self.s3_bucket = os.environ.get('S3_TEMP_BUCKET')
        if not self.s3_bucket:
            raise ValueError("S3_TEMP_BUCKET environment variable is required")
        
        # Validate S3 bucket name format (AWS S3 naming rules)
        # Bucket names must be 3-63 characters, lowercase, alphanumeric and hyphens
        bucket_pattern = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
        if not (3 <= len(self.s3_bucket) <= 63) or not bucket_pattern.match(self.s3_bucket):
            raise ValueError(f"Invalid S3 bucket name format: {self.s3_bucket}")
        
        # Initialize AWS clients
        # Note: AWS_REGION is automatically set by Lambda runtime
        # Use default only for local testing
        region = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2'))
        self.textract = boto3.client('textract', region_name=region)
        # Note: s3_client not needed - Textract accesses S3 directly via IAM role
        
        # Note: TEXTRACT_ROLE_ARN is not needed for synchronous analyze_document
        # It's only required for asynchronous operations
        self.role_arn = os.environ.get('TEXTRACT_ROLE_ARN')
    
    def process_document(self, s3_key, max_retries=3):
        """
        Process a document from S3 using Textract with retry logic
        Returns dictionary containing extracted text and structured data
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # Call Textract to analyse the document
                response = self.textract.analyze_document(
                    Document={
                        'S3Object': {
                            'Bucket': self.s3_bucket,
                            'Name': s3_key
                        }
                    },
                    FeatureTypes=['TABLES', 'FORMS']  # Extract tables and forms
                )
                
                # Extract and organise the text
                extracted_data = self._extract_text_data(response)
                
                return {
                    'success': True,
                    'text': extracted_data['full_text'],
                    'tables': extracted_data['tables'],
                    'forms': extracted_data['forms'],
                    'blocks': response.get('Blocks', [])
                }
                
            except ClientError as e:
                last_exception = e
                error_code = e.response.get('Error', {}).get('Code', '')
                
                # Retry on throttling errors
                if error_code == 'ThrottlingException' and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + (random.random() * 0.1)  # Exponential backoff with jitter
                    time.sleep(wait_time)
                    continue
                
                # Don't retry on other errors
                break
                
            except Exception as e:
                last_exception = e
                # Don't retry on non-ClientError exceptions
                break
        
        # Handle error after all retries exhausted or non-retryable error
        error_msg = self._sanitize_error(last_exception)
        
        return {
            'success': False,
            'error': error_msg,
            'text': '',
            'tables': [],
            'forms': []
        }
    
    def _sanitize_error(self, exception):
        """Sanitize AWS error messages to prevent information disclosure"""
        if not exception:
            return 'Document processing failed'
        
        error_msg = str(exception)
        error_type = type(exception).__name__
        
        # Fix: Comprehensive error sanitization using whitelist approach
        safe_errors = {
            'AccessDenied': 'Access denied to S3 bucket or document',
            'NoSuchBucket': 'S3 bucket or document not found',
            'InvalidParameter': 'Invalid document parameters',
            'ThrottlingException': 'Service temporarily unavailable',
            'InvalidS3ObjectException': 'Invalid document format',
            'UnsupportedDocumentException': 'Document type not supported',
            'BadDocumentException': 'Document cannot be processed',
            'ProvisionedThroughputExceededException': 'Service temporarily unavailable',
        }
        
        # Check error type first
        if error_type in safe_errors:
            return safe_errors[error_type]
        
        # Check for ClientError with error code
        if isinstance(exception, ClientError):
            error_code = exception.response.get('Error', {}).get('Code', '')
            if error_code in safe_errors:
                return safe_errors[error_code]
        
        # Check error message for known patterns
        error_msg_lower = error_msg.lower()
        if 'accessdenied' in error_msg_lower or '403' in error_msg:
            return 'Access denied to S3 bucket or document'
        elif 'nosuchbucket' in error_msg_lower or '404' in error_msg:
            return 'S3 bucket or document not found'
        elif 'throttling' in error_msg_lower or '503' in error_msg:
            return 'Service temporarily unavailable'
        
        # Generic sanitization - remove any AWS-specific details
        # Remove ARNs, account IDs, region names, etc.
        sanitized = re.sub(r'arn:aws:[^:]+:[^:]+:\d+:[^:]+', '[REDACTED]', error_msg)
        sanitized = re.sub(r'\d{12}', '[REDACTED]', sanitized)  # Account IDs
        sanitized = re.sub(r'us-[a-z]+-\d+', '[REDACTED]', sanitized)  # Regions
        
        # If still contains AWS-specific terms, return generic message
        if any(term in sanitized.lower() for term in ['aws', 's3', 'textract', 'boto']):
            return 'Document processing failed. Please verify the document exists and is accessible.'
        
        return sanitized if sanitized != error_msg else 'Document processing failed'
    
    def _extract_text_data(self, response):
        """
        Extract and organise text from Textract response
        Returns organised text data with tables and forms
        """
        blocks = response.get('Blocks', [])
        
        # Validate blocks is a list
        if not isinstance(blocks, list):
            blocks = []
        
        # Build a map of block IDs to blocks for quick lookup
        # Filter out blocks without 'Id' to prevent KeyError
        block_map = {block['Id']: block for block in blocks if 'Id' in block}
        
        # Extract full text
        full_text = []
        for block in blocks:
            if block.get('BlockType') == 'LINE':
                full_text.append(block.get('Text', ''))
        
        # Extract tables
        tables = self._extract_tables(blocks, block_map)
        
        # Extract forms (key-value pairs)
        forms = self._extract_forms(blocks, block_map)
        
        return {
            'full_text': '\n'.join(full_text),
            'tables': tables,
            'forms': forms
        }
    
    def _extract_tables(self, blocks, block_map):
        """
        Extract table structures from Textract blocks
        Returns list of extracted tables
        """
        tables = []
        
        # Find all TABLE blocks
        for block in blocks:
            # Skip blocks without required fields
            if block.get('BlockType') != 'TABLE':
                continue
            if 'Id' not in block:
                continue
                
            table_data = {
                'id': block['Id'],
                'rows': []
            }
            
            # Collect ALL cells from ALL CHILD relationships first
            all_cells = []
            if 'Relationships' in block:
                for relationship in block['Relationships']:
                    if relationship['Type'] == 'CHILD':
                        # Collect all cells from this relationship
                        cells = [block_map[cell_id] for cell_id in relationship['Ids'] 
                               if cell_id in block_map and block_map[cell_id].get('BlockType') == 'CELL']
                        all_cells.extend(cells)
            
            # Group all cells by row and column
            rows = {}
            for cell in all_cells:
                # Textract RowIndex and ColumnIndex start at 1, not 0
                # If missing or invalid, skip this cell
                row_index = cell.get('RowIndex')
                col_index = cell.get('ColumnIndex')
                
                # Skip cells with invalid or missing indices
                if not isinstance(row_index, int) or not isinstance(col_index, int):
                    continue
                if row_index < 1 or col_index < 1:
                    continue
                
                if row_index not in rows:
                    rows[row_index] = {}
                
                # Extract cell text
                cell_text = ''
                if 'Relationships' in cell:
                    for rel in cell['Relationships']:
                        if rel['Type'] == 'CHILD':
                            for word_id in rel['Ids']:
                                if word_id in block_map:
                                    word = block_map[word_id]
                                    if word.get('BlockType') == 'WORD':
                                        cell_text += word.get('Text', '') + ' '
                
                rows[row_index][col_index] = cell_text.strip()
            
            # Handle missing cells in sparse tables
            # Convert to list of rows, filling in missing cells
            if rows:
                max_row = max(rows.keys())
                # Find max column across all rows
                max_col = 0
                for r in rows.keys():
                    if rows[r] and rows[r].keys():
                        max_col = max(max_col, max(rows[r].keys()))
                
                # Build rows with proper column alignment
                if max_col > 0:  # Only process if table has columns
                    for row_idx in range(1, max_row + 1):
                        row = []
                        if row_idx in rows and rows[row_idx]:
                            for col_idx in range(1, max_col + 1):
                                if col_idx in rows[row_idx]:
                                    row.append(rows[row_idx][col_idx])
                                else:
                                    row.append('')  # Empty cell for missing data
                        else:
                            # Entire row is missing, fill with empty cells
                            row = [''] * max_col
                        table_data['rows'].append(row)
            
            tables.append(table_data)
        
        return tables
    
    def _extract_forms(self, blocks, block_map):
        """
        Extract form key-value pairs from Textract blocks
        Returns list of key-value pairs
        """
        forms = []
        
        # Find all KEY_VALUE_SET blocks
        for block in blocks:
            if block.get('BlockType') != 'KEY_VALUE_SET':
                continue
            
            entity_type = block.get('EntityTypes', [])
            
            if 'KEY' in entity_type:
                    # This is a key, find its value
                    key_text = ''
                    value_text = ''
                    
                    if 'Relationships' in block:
                        for relationship in block['Relationships']:
                            if relationship['Type'] == 'CHILD':
                                # Get key text
                                for word_id in relationship['Ids']:
                                    if word_id in block_map:
                                        word = block_map[word_id]
                                        if word.get('BlockType') == 'WORD':
                                            key_text += word.get('Text', '') + ' '
                            
                            elif relationship['Type'] == 'VALUE':
                                # Get value text
                                for value_id in relationship['Ids']:
                                    if value_id in block_map:
                                        value_block = block_map[value_id]
                                        if 'Relationships' in value_block:
                                            for rel in value_block['Relationships']:
                                                if rel['Type'] == 'CHILD':
                                                    for word_id in rel['Ids']:
                                                        if word_id in block_map:
                                                            word = block_map[word_id]
                                                            if word.get('BlockType') == 'WORD':
                                                                value_text += word.get('Text', '') + ' '
                    
                    if key_text.strip():
                        forms.append({
                            'key': key_text.strip(),
                            'value': value_text.strip()
                        })
        
        return forms