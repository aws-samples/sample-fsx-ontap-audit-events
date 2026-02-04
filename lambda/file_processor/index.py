"""
FSx ONTAP File Processor Lambda Function

Processes file creation events from SQS queue.
Generates thumbnails for image files and writes them back to FSx ONTAP.
"""

import boto3
import json
import os
import io
from typing import Dict

try:
    from PIL import Image
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    print("Pillow not available")

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
S3_ACCESS_POINT_ALIAS = os.environ.get('S3_ACCESS_POINT_ALIAS', '')
OUTPUT_S3_ACCESS_POINT_ALIAS = os.environ.get('OUTPUT_S3_ACCESS_POINT_ALIAS', S3_ACCESS_POINT_ALIAS)

# Supported image formats
SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.tif'}


def lambda_handler(event, context):
    """Main Lambda handler for file processing."""
    print(f"Processing {len(event['Records'])} file events")
    
    processed = 0
    errors = 0
    
    for record in event['Records']:
        try:
            file_event = json.loads(record['body'])
            
            if process_file_event(file_event):
                processed += 1
            
        except Exception as e:
            print(f"Error processing record: {e}")
            errors += 1
            raise  # Retry via SQS
    
    print(f"Processed {processed} files, {errors} errors")
    
    return {
        'statusCode': 200,
        'processed': processed,
        'errors': errors
    }


def process_file_event(file_event: Dict) -> bool:
    """Process a single file event."""
    file_path = file_event['file_path']
    operation = file_event['operation']
    
    print(f"Processing {operation} on {file_path}")
    
    # Check if file is an image
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in SUPPORTED_FORMATS:
        print(f"Skipping non-image file: {file_path}")
        return False
    
    # Only process create operations
    if operation != 'create':
        print(f"Skipping {operation} operation")
        return False
    
    if not PILLOW_AVAILABLE:
        print("Pillow not available, cannot process images")
        return False
    
    try:
        # Read original image via S3 Access Point
        response = s3.get_object(
            Bucket=S3_ACCESS_POINT_ALIAS,
            Key=file_path
        )
        image_bytes = response['Body'].read()
        
        # Generate thumbnail
        thumbnail_bytes = generate_thumbnail(image_bytes)
        
        # Write thumbnail to OUTPUT access point (separate volume to avoid loop)
        thumbnail_path = f"/thumbnails{file_path}"
        s3.put_object(
            Bucket=OUTPUT_S3_ACCESS_POINT_ALIAS,
            Key=thumbnail_path,
            Body=thumbnail_bytes,
            ContentType='image/jpeg',
            Metadata={
                'original-path': file_path,
                'thumbnail-size': '200x200',
                'generated-by': 'fsx-audit-processor'
            }
        )
        
        print(f"Generated thumbnail: {thumbnail_path}")
        return True
        
    except s3.exceptions.NoSuchKey:
        print(f"File not found: {file_path} (may have been deleted)")
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        raise


def generate_thumbnail(image_bytes: bytes, max_size=(200, 200)) -> bytes:
    """Generate thumbnail from image bytes."""
    try:
        # Open image from bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if necessary (for JPEG)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'RGBA':
                background.paste(image, mask=image.split()[-1])
            else:
                background.paste(image)
            image = background
        
        # Generate thumbnail (maintains aspect ratio)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        raise


# Generic processing examples for documentation

def extract_metadata(file_path: str, file_content: bytes) -> Dict:
    """
    Example: Extract file metadata.
    
    This is a placeholder showing how to implement custom processing logic.
    """
    import mimetypes
    
    metadata = {
        'file_path': file_path,
        'size': len(file_content),
        'mime_type': mimetypes.guess_type(file_path)[0],
        'extension': os.path.splitext(file_path)[1]
    }
    
    return metadata


def scan_file(file_path: str, file_content: bytes) -> Dict:
    """
    Example: Scan file for viruses.
    
    This is a placeholder showing how to integrate with scanning services.
    Integrate with ClamAV or third-party scanning service.
    """
    scan_result = {
        'file_path': file_path,
        'clean': True,
        'threats': []
    }
    
    return scan_result
