# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Unit tests for file processor Lambda function.
"""

import pytest
import json
from io import BytesIO
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import importlib.util

# Load the file processor module directly
spec = importlib.util.spec_from_file_location(
    "file_processor_index",
    os.path.join(os.path.dirname(__file__), '..', 'lambda', 'file_processor', 'index.py')
)
file_processor_index = importlib.util.module_from_spec(spec)
spec.loader.exec_module(file_processor_index)

# Mock PIL if not available
try:
    from PIL import Image
except ImportError:
    Image = None


class TestFileProcessing:
    """Test file event processing."""
    
    @patch.object(file_processor_index, 's3')
    @patch.object(file_processor_index, 'PILLOW_AVAILABLE', True)
    def test_process_image_file(self, mock_s3):
        """Test processing image file."""
        if Image is None:
            pytest.skip("PIL not available")
        
        # Create test image
        img = Image.new('RGB', (800, 600), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': MagicMock(read=lambda: buffer.getvalue())
        }
        
        file_event = {
            'file_path': '/data/test.jpg',
            'operation': 'create'
        }
        
        result = file_processor_index.process_file_event(file_event)
        
        assert result is True
        assert mock_s3.put_object.called
        
        # Verify thumbnail path
        put_call = mock_s3.put_object.call_args
        assert put_call[1]['Key'] == '/thumbnails/data/test.jpg'
    
    def test_process_non_image_file(self):
        """Test skipping non-image files."""
        file_event = {
            'file_path': '/data/document.pdf',
            'operation': 'create'
        }
        
        result = file_processor_index.process_file_event(file_event)
        
        assert result is False
    
    def test_process_non_create_operation(self):
        """Test skipping non-create operations."""
        file_event = {
            'file_path': '/data/test.jpg',
            'operation': 'read'
        }
        
        result = file_processor_index.process_file_event(file_event)
        
        assert result is False


class TestThumbnailGeneration:
    """Test thumbnail generation logic."""
    
    def test_generate_thumbnail_jpeg(self):
        """Test generating thumbnail from JPEG."""
        if Image is None:
            pytest.skip("PIL not available")
        
        # Create test image
        img = Image.new('RGB', (800, 600), color='red')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        thumbnail_bytes = file_processor_index.generate_thumbnail(buffer.getvalue())
        
        # Verify thumbnail
        thumb_img = Image.open(BytesIO(thumbnail_bytes))
        assert thumb_img.size[0] <= 200
        assert thumb_img.size[1] <= 200
        assert thumb_img.format == 'JPEG'
    
    def test_generate_thumbnail_png_with_transparency(self):
        """Test generating thumbnail from PNG with transparency."""
        if Image is None:
            pytest.skip("PIL not available")
        
        # Create test image with alpha channel
        img = Image.new('RGBA', (800, 600), color=(255, 0, 0, 128))
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        thumbnail_bytes = file_processor_index.generate_thumbnail(buffer.getvalue())
        
        # Verify thumbnail (should be converted to RGB/JPEG)
        thumb_img = Image.open(BytesIO(thumbnail_bytes))
        assert thumb_img.mode == 'RGB'
        assert thumb_img.format == 'JPEG'
    
    def test_generate_thumbnail_aspect_ratio(self):
        """Test thumbnail maintains aspect ratio."""
        if Image is None:
            pytest.skip("PIL not available")
        
        # Create wide image
        img = Image.new('RGB', (1600, 400), color='green')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)
        
        thumbnail_bytes = file_processor_index.generate_thumbnail(buffer.getvalue())
        
        # Verify aspect ratio maintained
        thumb_img = Image.open(BytesIO(thumbnail_bytes))
        assert thumb_img.size[0] == 200  # Width should be max
        assert thumb_img.size[1] == 50   # Height should maintain ratio


class TestLambdaHandler:
    """Test main Lambda handler."""
    
    @patch.object(file_processor_index, 'process_file_event')
    def test_lambda_handler_success(self, mock_process):
        """Test successful Lambda execution."""
        mock_process.return_value = True
        
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'file_path': '/data/test1.jpg',
                        'operation': 'create'
                    })
                },
                {
                    'body': json.dumps({
                        'file_path': '/data/test2.jpg',
                        'operation': 'create'
                    })
                }
            ]
        }
        
        result = file_processor_index.lambda_handler(event, None)
        
        assert result['statusCode'] == 200
        assert result['processed'] == 2
        assert result['errors'] == 0
    
    @patch.object(file_processor_index, 'process_file_event')
    def test_lambda_handler_with_errors(self, mock_process):
        """Test Lambda execution with errors."""
        mock_process.side_effect = Exception("Processing error")
        
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'file_path': '/data/test.jpg',
                        'operation': 'create'
                    })
                }
            ]
        }
        
        with pytest.raises(Exception):
            file_processor_index.lambda_handler(event, None)


class TestGenericProcessingExamples:
    """Test generic processing example functions."""
    
    def test_extract_metadata(self):
        """Test metadata extraction example."""
        metadata = file_processor_index.extract_metadata('/data/test.jpg', b'fake image data')
        
        assert metadata['file_path'] == '/data/test.jpg'
        assert metadata['size'] == len(b'fake image data')
        assert metadata['extension'] == '.jpg'
    
    def test_scan_file(self):
        """Test file scanning example."""
        result = file_processor_index.scan_file('/data/test.jpg', b'fake image data')
        
        assert result['file_path'] == '/data/test.jpg'
        assert result['clean'] is True
        assert isinstance(result['threats'], list)
