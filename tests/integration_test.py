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

#!/usr/bin/env python3
"""
Integration test for FSx ONTAP Audit Event Processing.

Tests the complete workflow:
1. Create test image
2. Upload to FSx via S3 Access Point
3. Generate simulated audit log
4. Process audit log
5. Verify thumbnail generation
"""

import argparse
import boto3
import json
import sys
import time
from datetime import datetime
from io import BytesIO
from PIL import Image

# Initialize AWS clients
s3 = boto3.client('s3')


def create_test_image(width=800, height=600) -> bytes:
    """Create a test image."""
    print("Creating test image...")
    img = Image.new('RGB', (width, height), color='blue')
    
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    
    return buffer.getvalue()


def upload_test_file(s3_alias: str, file_path: str, content: bytes):
    """Upload test file to FSx via S3 Access Point."""
    print(f"Uploading test file to {file_path}...")
    
    s3.put_object(
        Bucket=s3_alias,
        Key=file_path,
        Body=content,
        ContentType='image/jpeg'
    )
    
    print(f"✓ File uploaded: {file_path}")


def create_simulated_audit_log(file_path: str) -> str:
    """Create a simulated ONTAP audit log in XML format."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    
    xml_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4656</EventID>
      <EventName>Open Object</EventName>
      <Source>CIFS</Source>
      <TimeCreated SystemTime="{timestamp}"/>
      <Computer>FsxId0a60f59a70d0b2b4a/fsxz_s01</Computer>
    </System>
    <EventData>
      <Data Name="SubjectUserName">testuser</Data>
      <Data Name="SubjectDomainName">FSXZ_S01</Data>
      <Data Name="SubjectIP" IPVersion="4">172.31.18.58</Data>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(ntfs);{file_path}</Data>
      <Data Name="HandleID">00000000000411;00;00000040;63f61953</Data>
    </EventData>
  </Event>
</Events>'''
    
    return xml_content


def upload_audit_log(s3_alias: str, audit_prefix: str, content: str):
    """Upload simulated audit log."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d-T%H-%M-%S')
    log_filename = f"audit_test_D{timestamp}_0000000000.xml"
    log_key = f"{audit_prefix}{log_filename}"
    
    print(f"Uploading audit log: {log_key}...")
    
    s3.put_object(
        Bucket=s3_alias,
        Key=log_key,
        Body=content.encode('utf-8'),
        ContentType='application/xml'
    )
    
    print(f"✓ Audit log uploaded: {log_key}")
    return log_key


def verify_thumbnail(s3_alias: str, thumbnail_path: str, max_retries=5, delay=10):
    """Verify thumbnail was created."""
    print(f"Verifying thumbnail at {thumbnail_path}...")
    
    for attempt in range(max_retries):
        try:
            response = s3.head_object(Bucket=s3_alias, Key=thumbnail_path)
            print(f"✓ Thumbnail verified: {thumbnail_path}")
            print(f"  Size: {response['ContentLength']} bytes")
            print(f"  Content-Type: {response.get('ContentType', 'unknown')}")
            
            # Verify it's a valid image
            obj = s3.get_object(Bucket=s3_alias, Key=thumbnail_path)
            img_data = obj['Body'].read()
            img = Image.open(BytesIO(img_data))
            print(f"  Dimensions: {img.size[0]}x{img.size[1]}")
            
            return True
            
        except s3.exceptions.NoSuchKey:
            if attempt < max_retries - 1:
                print(f"  Thumbnail not found yet, retrying in {delay}s... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"✗ Thumbnail not found after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"✗ Error verifying thumbnail: {e}")
            return False
    
    return False


def test_audit_log_parsing(audit_log_content: str, file_path: str):
    """Test audit log parsing logic."""
    print("\nTesting audit log parsing...")
    
    import defusedxml.ElementTree as ET
    
    try:
        root = ET.fromstring(audit_log_content)
        events = []
        
        for event_elem in root.findall('.//Event'):
            system = event_elem.find('System')
            event_data = event_elem.find('EventData')
            
            if system is None or event_data is None:
                continue
            
            event_id_elem = system.find('EventID')
            if event_id_elem is None or event_id_elem.text != '4656':
                continue
            
            # Extract object type and name
            object_type = None
            object_name = None
            
            for data in event_data.findall('Data'):
                name = data.get('Name')
                if name == 'ObjectType':
                    object_type = data.text
                elif name == 'ObjectName':
                    object_name = data.text
            
            if object_type == 'File' and object_name:
                parsed_path = object_name.split(';', 1)[1] if ';' in object_name else object_name
                events.append({
                    'file_path': parsed_path,
                    'operation': 'create'
                })
        
        if events:
            print(f"✓ Parsed {len(events)} file event(s)")
            for event in events:
                print(f"  - {event['file_path']}")
            
            if events[0]['file_path'] == file_path:
                print(f"✓ File path matches: {file_path}")
                return True
            else:
                print(f"✗ File path mismatch: expected {file_path}, got {events[0]['file_path']}")
                return False
        else:
            print("✗ No events parsed")
            return False
            
    except Exception as e:
        print(f"✗ Error parsing audit log: {e}")
        return False


def test_thumbnail_generation(image_bytes: bytes):
    """Test thumbnail generation logic."""
    print("\nTesting thumbnail generation...")
    
    try:
        img = Image.open(BytesIO(image_bytes))
        print(f"✓ Original image: {img.size[0]}x{img.size[1]}, mode={img.mode}")
        
        # Generate thumbnail
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        thumbnail_bytes = output.getvalue()
        
        # Verify thumbnail
        thumb_img = Image.open(BytesIO(thumbnail_bytes))
        print(f"✓ Thumbnail generated: {thumb_img.size[0]}x{thumb_img.size[1]}")
        print(f"✓ Thumbnail size: {len(thumbnail_bytes)} bytes")
        
        return True
        
    except Exception as e:
        print(f"✗ Error generating thumbnail: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Integration test for FSx ONTAP Audit Event Processing')
    parser.add_argument('--audit-alias', required=True, help='S3 Access Point alias for audit logs')
    parser.add_argument('--file-alias', required=True, help='S3 Access Point alias for file data')
    parser.add_argument('--audit-prefix', default='audit/', help='Audit log prefix (default: audit/)')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    
    args = parser.parse_args()
    
    # Update boto3 client with region
    global s3
    s3 = boto3.client('s3', region_name=args.region)
    
    print("=" * 60)
    print("FSx ONTAP Audit Event Processing - Integration Test")
    print("=" * 60)
    
    # Test file path
    test_file_path = '/data/test_image.jpg'
    thumbnail_path = f'/thumbnails{test_file_path}'
    
    # Step 1: Create test image
    print("\n[Step 1] Creating test image...")
    image_bytes = create_test_image()
    print(f"✓ Test image created: {len(image_bytes)} bytes")
    
    # Step 2: Test thumbnail generation locally
    if not test_thumbnail_generation(image_bytes):
        print("\n✗ Thumbnail generation test failed")
        sys.exit(1)
    
    # Step 3: Upload test file
    print(f"\n[Step 2] Uploading test file to FSx...")
    try:
        upload_test_file(args.file_alias, test_file_path, image_bytes)
    except Exception as e:
        print(f"✗ Failed to upload test file: {e}")
        sys.exit(1)
    
    # Step 4: Create and test audit log parsing
    print(f"\n[Step 3] Creating simulated audit log...")
    audit_log_content = create_simulated_audit_log(test_file_path)
    
    if not test_audit_log_parsing(audit_log_content, test_file_path):
        print("\n✗ Audit log parsing test failed")
        sys.exit(1)
    
    # Step 5: Upload audit log
    print(f"\n[Step 4] Uploading audit log...")
    try:
        log_key = upload_audit_log(args.audit_alias, args.audit_prefix, audit_log_content)
    except Exception as e:
        print(f"✗ Failed to upload audit log: {e}")
        sys.exit(1)
    
    # Step 6: Wait for processing and verify thumbnail
    print(f"\n[Step 5] Waiting for thumbnail generation...")
    print("(This may take 60-120 seconds due to EventBridge schedule)")
    
    if verify_thumbnail(args.file_alias, thumbnail_path, max_retries=15, delay=10):
        print("\n" + "=" * 60)
        print("✓ Integration test PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗ Integration test FAILED")
        print("=" * 60)
        print("\nTroubleshooting:")
        print("1. Check Lambda logs in CloudWatch")
        print("2. Verify EventBridge rule is enabled")
        print("3. Check SQS queue for messages")
        print("4. Verify IAM permissions")
        sys.exit(1)


if __name__ == '__main__':
    main()
