#!/usr/bin/env python3
"""
Integration test for FSx ONTAP audit event processing.

This script tests the end-to-end flow:
1. Write a test image to FSx via S3 Access Point
2. Simulate audit log generation
3. Process the audit log
4. Generate thumbnail
5. Verify thumbnail exists

Usage:
    python integration_test.py --audit-alias <audit-ap-alias> --file-alias <file-ap-alias>
"""
import argparse
import boto3
import json
import time
from datetime import datetime
from pathlib import Path


def create_test_image():
    """Create a simple test image."""
    try:
        from PIL import Image
        img = Image.new('RGB', (800, 600), color='blue')
        img.save('/tmp/test_image.jpg')
        print("✓ Created test image: /tmp/test_image.jpg")
        return '/tmp/test_image.jpg'
    except ImportError:
        print("✗ Pillow not installed. Install with: pip install Pillow")
        return None


def upload_file_to_fsx(s3_client, file_alias, local_path, remote_path):
    """Upload file to FSx via S3 Access Point."""
    try:
        with open(local_path, 'rb') as f:
            s3_client.put_object(
                Bucket=file_alias,
                Key=remote_path,
                Body=f
            )
        print(f"✓ Uploaded {local_path} to {file_alias}/{remote_path}")
        return True
    except Exception as e:
        print(f"✗ Failed to upload: {e}")
        return False


def simulate_audit_log(s3_client, audit_alias, file_path):
    """Create a simulated audit log entry."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    
    audit_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4656</EventID>
      <EventName>Open Object</EventName>
      <Source>CIFS</Source>
      <TimeCreated SystemTime="{timestamp}"/>
      <Computer>FsxId/test_svm</Computer>
    </System>
    <EventData>
      <Data Name="SubjectUserName">testuser</Data>
      <Data Name="SubjectDomainName">TEST</Data>
      <Data Name="SubjectIP" IPVersion="4">127.0.0.1</Data>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(ntfs);{file_path}</Data>
      <Data Name="HandleID">00000000000001;00;00000040;00000001</Data>
    </EventData>
  </Event>
</Events>
"""
    
    log_filename = f"audit/audit_test_D{datetime.utcnow().strftime('%Y-%m-%d-T%H-%M-%S')}_0000000000.xml"
    
    try:
        s3_client.put_object(
            Bucket=audit_alias,
            Key=log_filename,
            Body=audit_xml.encode('utf-8')
        )
        print(f"✓ Created simulated audit log: {log_filename}")
        return log_filename
    except Exception as e:
        print(f"✗ Failed to create audit log: {e}")
        return None


def parse_audit_log(s3_client, audit_alias, log_key):
    """Parse audit log and extract file events."""
    try:
        response = s3_client.get_object(Bucket=audit_alias, Key=log_key)
        content = response['Body'].read()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)
        
        events = []
        for event_elem in root.findall('.//Event'):
            system = event_elem.find('System')
            event_data = event_elem.find('EventData')
            
            event_id = system.find('EventID').text
            
            if event_id == '4656':
                object_type = None
                object_name = None
                
                for data in event_data.findall('Data'):
                    name = data.get('Name')
                    if name == 'ObjectType':
                        object_type = data.text
                    elif name == 'ObjectName':
                        object_name = data.text
                
                if object_type == 'File' and object_name:
                    file_path = object_name.split(';', 1)[1] if ';' in object_name else object_name
                    events.append({
                        'file_path': file_path,
                        'operation': 'create',
                        'timestamp': system.find('TimeCreated').get('SystemTime'),
                    })
        
        print(f"✓ Parsed audit log: found {len(events)} file events")
        return events
    except Exception as e:
        print(f"✗ Failed to parse audit log: {e}")
        return []


def generate_thumbnail(s3_client, file_alias, file_path):
    """Generate thumbnail for image file."""
    try:
        from PIL import Image
        import io
        
        # Read original image
        response = s3_client.get_object(Bucket=file_alias, Key=file_path)
        image_bytes = response['Body'].read()
        
        # Generate thumbnail
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        # Convert to bytes
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=85)
        output.seek(0)
        thumbnail_bytes = output.getvalue()
        
        # Write thumbnail
        thumbnail_path = f"/thumbnails{file_path}"
        s3_client.put_object(
            Bucket=file_alias,
            Key=thumbnail_path,
            Body=thumbnail_bytes,
            ContentType='image/jpeg'
        )
        
        print(f"✓ Generated thumbnail: {thumbnail_path}")
        return thumbnail_path
    except Exception as e:
        print(f"✗ Failed to generate thumbnail: {e}")
        return None


def verify_thumbnail(s3_client, file_alias, thumbnail_path):
    """Verify thumbnail exists and is accessible."""
    try:
        response = s3_client.head_object(Bucket=file_alias, Key=thumbnail_path)
        size = response['ContentLength']
        print(f"✓ Thumbnail verified: {thumbnail_path} ({size} bytes)")
        return True
    except Exception as e:
        print(f"✗ Thumbnail not found: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Test FSx ONTAP audit event processing')
    parser.add_argument('--audit-alias', required=True, help='S3 Access Point alias for audit logs')
    parser.add_argument('--file-alias', required=True, help='S3 Access Point alias for file data')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("FSx ONTAP Audit Event Processing - Integration Test")
    print("="*60 + "\n")
    
    s3_client = boto3.client('s3', region_name=args.region)
    
    # Step 1: Create test image
    print("Step 1: Creating test image...")
    test_image = create_test_image()
    if not test_image:
        return
    
    # Step 2: Upload to FSx via S3 Access Point
    print("\nStep 2: Uploading test image to FSx...")
    remote_path = "/data/test_image.jpg"
    if not upload_file_to_fsx(s3_client, args.file_alias, test_image, remote_path):
        return
    
    # Step 3: Simulate audit log generation
    print("\nStep 3: Simulating audit log generation...")
    log_key = simulate_audit_log(s3_client, args.audit_alias, remote_path)
    if not log_key:
        return
    
    # Step 4: Parse audit log
    print("\nStep 4: Parsing audit log...")
    events = parse_audit_log(s3_client, args.audit_alias, log_key)
    if not events:
        return
    
    # Step 5: Generate thumbnail
    print("\nStep 5: Generating thumbnail...")
    thumbnail_path = generate_thumbnail(s3_client, args.file_alias, events[0]['file_path'])
    if not thumbnail_path:
        return
    
    # Step 6: Verify thumbnail
    print("\nStep 6: Verifying thumbnail...")
    if verify_thumbnail(s3_client, args.file_alias, thumbnail_path):
        print("\n" + "="*60)
        print("✓ Integration test PASSED!")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("✗ Integration test FAILED!")
        print("="*60 + "\n")


if __name__ == '__main__':
    main()
