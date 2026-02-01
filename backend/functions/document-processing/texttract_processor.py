import boto3
import os

class TextractProcessor:
    """
    Handles AWS Textract document processing
    Extracts text and structured data from images
    """
    
    def __init__(self):
        """Initialise Textract client"""
        self.textract = boto3.client('textract', region_name=os.environ.get('AWS_REGION', 'eu-west-2'))
        self.role_arn = os.environ.get('TEXTRACT_ROLE_ARN')
        self.s3_client = boto3.client('s3')
        self.s3_bucket = os.environ.get('S3_TEMP_BUCKET')
    
    def process_document(self, s3_key):
        """
        Process a document from S3 using Textract
        Returns dictionary containing extracted text and structured data
        """
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
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'tables': [],
                'forms': []
            }
    
    def _extract_text_data(self, response):
        """
        Extract and organise text from Textract response
        Returns organised text data with tables and forms
        """
        blocks = response.get('Blocks', [])
        
        # Build a map of block IDs to blocks for quick lookup
        block_map = {block['Id']: block for block in blocks}
        
        # Extract full text
        full_text = []
        for block in blocks:
            if block['BlockType'] == 'LINE':
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
            if block['BlockType'] == 'TABLE':
                table_data = {
                    'id': block['Id'],
                    'rows': []
                }
                
                # Get all cells in this table
                if 'Relationships' in block:
                    for relationship in block['Relationships']:
                        if relationship['Type'] == 'CHILD':
                            # Process cells to build rows
                            cells = [block_map[cell_id] for cell_id in relationship['Ids'] 
                                   if cell_id in block_map and block_map[cell_id]['BlockType'] == 'CELL']
                            
                            # Group cells by row
                            rows = {}
                            for cell in cells:
                                row_index = cell.get('RowIndex', 0)
                                col_index = cell.get('ColumnIndex', 0)
                                
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
                                                    if word['BlockType'] == 'WORD':
                                                        cell_text += word.get('Text', '') + ' '
                                
                                rows[row_index][col_index] = cell_text.strip()
                            
                            # Convert to list of rows
                            for row_idx in sorted(rows.keys()):
                                row = []
                                for col_idx in sorted(rows[row_idx].keys()):
                                    row.append(rows[row_idx][col_idx])
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
            if block['BlockType'] == 'KEY_VALUE_SET':
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
                                        if word['BlockType'] == 'WORD':
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
                                                            if word['BlockType'] == 'WORD':
                                                                value_text += word.get('Text', '') + ' '
                    
                    if key_text.strip():
                        forms.append({
                            'key': key_text.strip(),
                            'value': value_text.strip()
                        })
        
        return forms