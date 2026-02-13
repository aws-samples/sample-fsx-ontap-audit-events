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
FSx ONTAP Audit Log Processor Lambda Function

Processes ONTAP audit logs (XML/EVTX format) to extract file creation events.
Uses checkpoint-based approach with DynamoDB for efficient processing.
Publishes events to EventBridge for flexible downstream routing.
"""

import boto3
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional

# Initialize AWS clients
s3 = boto3.client('s3')
events_client = boto3.client('events')
sqs_client = boto3.client('sqs')
sns_client = boto3.client('sns')
logs_client = boto3.client('logs')
dynamodb = boto3.resource('dynamodb')

# Environment variables
BUCKET = os.environ.get('BUCKET', '')
AUDIT_PREFIX = os.environ.get('AUDIT_PREFIX', 'audit/')
TABLE_NAME = os.environ.get('TABLE_NAME', '')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', '')
MAX_KEYS = int(os.environ.get('MAX_KEYS', '100'))
MAX_LOGS_PER_INVOCATION = int(os.environ.get('MAX_LOGS_PER_INVOCATION', '10'))
ROUTING_CONFIG = os.environ.get('ROUTING_CONFIG', '')

# Parse routing config on module load
_routes: Dict[tuple, Dict] = {}

if ROUTING_CONFIG:
    try:
        _config = json.loads(ROUTING_CONFIG)
        for route in _config.get('routes', []):
            if 'svm_name' in route and 'junction_path' in route:
                key = (route['svm_name'], route['junction_path'])
                _routes[key] = route
        print(f"Loaded {len(_routes)} routing rules")
    except json.JSONDecodeError as e:
        print(f"Error parsing ROUTING_CONFIG: {e}")


def get_route(svm_name: str, junction_path: str) -> Optional[Dict]:
    """Look up route config by svm_name and junction_path."""
    return _routes.get((svm_name, junction_path))

# DynamoDB table
if TABLE_NAME:
    table = dynamodb.Table(TABLE_NAME)
else:
    table = None

# Try to import EVTX parser (optional)
try:
    from Evtx.Evtx import Evtx
    from Evtx.Views import evtx_file_xml_view
    import tempfile
    EVTX_AVAILABLE = True
except ImportError as e:
    EVTX_AVAILABLE = False
    print(f"EVTX parser not available: {e}")


def lambda_handler(event, context):
    """Main Lambda handler for audit log processing."""
    print(f"Starting audit log processing at {datetime.utcnow().isoformat()}")
    
    # Step 1: Get checkpoint from DynamoDB
    checkpoint = get_checkpoint()
    last_processed = checkpoint.get('last_processed_log', '')
    
    # First run: skip to latest log to avoid processing backlog
    if not last_processed:
        last_processed = initialize_checkpoint_to_latest()
        if not last_processed:
            print("No logs found, waiting for first log")
            return {'statusCode': 200, 'logs_processed': 0}
    
    print(f"Last processed log: {last_processed}")
    
    # Step 2: List new audit logs (limited per invocation)
    new_logs = list_new_logs(last_processed)
    
    if not new_logs:
        print("No new logs to process")
        return {'statusCode': 200, 'logs_processed': 0}
    
    # Limit logs per invocation to reduce failure blast radius
    logs_to_process = new_logs[:MAX_LOGS_PER_INVOCATION]
    print(f"Processing {len(logs_to_process)} of {len(new_logs)} new logs")
    
    # Step 3: Process each log with per-log checkpointing
    events_processed = 0
    logs_completed = 0
    
    for log_key in logs_to_process:
        try:
            log_events = process_audit_log(log_key)
            if log_events:
                publish_events(log_events)
                events_processed += len(log_events)
            
            # Checkpoint after each successful log to ensure at-least-once
            update_checkpoint(extract_filename(log_key), 1)
            logs_completed += 1
            
        except Exception as e:
            print(f"Error processing {log_key}, stopping: {e}")
            break  # Stop on failure to avoid gaps
    
    print(f"Processed {logs_completed} logs, found {events_processed} file events")
    
    return {
        'statusCode': 200,
        'logs_processed': logs_completed,
        'events_found': events_processed
    }


def get_checkpoint() -> Dict:
    """Get checkpoint from DynamoDB."""
    try:
        response = table.get_item(Key={'pk': 'tracker'})
        return response.get('Item', {
            'pk': 'tracker',
            'last_processed_log': '',
            'last_check_time': '2000-01-01T00:00:00Z',
            'processed_count': 0
        })
    except Exception as e:
        print(f"Error reading checkpoint: {e}")
        return {
            'pk': 'tracker',
            'last_processed_log': '',
            'last_check_time': '2000-01-01T00:00:00Z',
            'processed_count': 0
        }


def update_checkpoint(last_log: str, count: int):
    """Update checkpoint in DynamoDB."""
    try:
        table.update_item(
            Key={'pk': 'tracker'},
            UpdateExpression='SET last_processed_log = :log, last_check_time = :time, processed_count = if_not_exists(processed_count, :zero) + :count',
            ExpressionAttributeValues={
                ':log': last_log,
                ':time': datetime.utcnow().isoformat(),
                ':count': count,
                ':zero': 0
            }
        )
    except Exception as e:
        print(f"Error updating checkpoint: {e}")
        raise


def initialize_checkpoint_to_latest() -> str:
    """On first run, skip to the latest completed log to avoid backlog processing."""
    try:
        response = s3.list_objects_v2(Bucket=BUCKET, Prefix=AUDIT_PREFIX, MaxKeys=1000)
        if 'Contents' not in response:
            return ''
        
        all_logs = sorted([obj['Key'] for obj in response['Contents']])
        # Filter out active log
        completed = [l for l in all_logs if '_last.' not in l]
        
        if not completed:
            return ''
        
        # Use second-to-last log as checkpoint (last completed one)
        latest = extract_filename(completed[-1])
        print(f"First run: initializing checkpoint to latest log: {latest}")
        update_checkpoint(latest, 0)
        return latest
    except Exception as e:
        print(f"Error initializing checkpoint: {e}")
        return ''


def list_new_logs(last_processed: str) -> List[str]:
    """List new audit logs using StartAfter optimization."""
    try:
        params = {
            'Bucket': BUCKET,
            'Prefix': AUDIT_PREFIX,
            'MaxKeys': MAX_KEYS
        }
        
        # Use StartAfter for efficient pagination
        if last_processed:
            params['StartAfter'] = f"{AUDIT_PREFIX}{last_processed}"
        
        print(f"Listing S3 objects with params: {params}")
        response = s3.list_objects_v2(**params)
        print(f"S3 response: IsTruncated={response.get('IsTruncated')}, KeyCount={response.get('KeyCount', 0)}")
        
        if 'Contents' not in response:
            print("No Contents in S3 response")
            return []
        
        all_logs = [obj['Key'] for obj in response['Contents']]
        print(f"Found {len(all_logs)} total objects")
        
        # Identify and filter out active log
        is_truncated = response.get('IsTruncated', False)
        active_log = identify_active_log(all_logs, is_truncated)
        
        if active_log:
            print(f"Active log identified: {active_log}")
        
        completed_logs = [log for log in all_logs if log != active_log]
        completed_logs.sort()  # Ensure chronological order
        
        print(f"Completed logs to process: {len(completed_logs)}")
        
        return completed_logs
        
    except Exception as e:
        print(f"Error listing logs: {e}")
        import traceback
        traceback.print_exc()
        raise


def identify_active_log(logs: List[str], is_truncated: bool) -> Optional[str]:
    """Identify the active log file being written."""
    # Check for _last.xml or _last.evtx
    for log in logs:
        if '_last.' in log:
            return log
    
    # If not truncated and we have logs, newest (last) file is active
    if not is_truncated and logs:
        return logs[-1]
    
    return None


def process_audit_log(log_key: str) -> List[Dict]:
    """Process a single audit log file."""
    print(f"Processing: {log_key}")
    
    try:
        # Download file from S3
        response = s3.get_object(Bucket=BUCKET, Key=log_key)
        content = response['Body'].read()
        
        # Auto-detect format by extension
        if log_key.endswith('.xml'):
            events = parse_xml_audit(content, log_key)
        elif log_key.endswith('.evtx'):
            events = parse_evtx_audit(content, log_key)
        else:
            print(f"Unknown format for {log_key}")
            return []
        
        print(f"Found {len(events)} file events in {log_key}")
        return events
        
    except Exception as e:
        print(f"Error processing {log_key}: {e}")
        raise


def parse_xml_audit(content: bytes, log_key: str) -> List[Dict]:
    """Parse Windows Event Log XML format with namespace support."""
    events = []
    
    try:
        root = ET.fromstring(content)
        
        # Handle XML namespace
        ns = {'ns': 'http://www.netapp.com/schemas/ONTAP/2007/AuditLog'}
        
        # Find all Event elements (try with namespace first, then without)
        event_elements = root.findall('.//ns:Event', ns)
        if not event_elements:
            event_elements = root.findall('.//Event')
        
        print(f"Found {len(event_elements)} Event elements in XML")
        
        for event_elem in event_elements:
            # Try with namespace first, then without (use explicit None check)
            system = event_elem.find('ns:System', ns)
            if system is None:
                system = event_elem.find('System')
            event_data = event_elem.find('ns:EventData', ns)
            if event_data is None:
                event_data = event_elem.find('EventData')
            
            if system is None or event_data is None:
                continue
            
            # Extract event ID (use explicit None check)
            event_id_elem = system.find('ns:EventID', ns)
            if event_id_elem is None:
                event_id_elem = system.find('EventID')
            if event_id_elem is None:
                continue
            
            event_id = event_id_elem.text
            
            # Filter for file creation (4656)
            if event_id != '4656':
                continue
            
            # Extract object type and name
            object_type = get_event_data_value(event_data, 'ObjectType', ns)
            object_name = get_event_data_value(event_data, 'ObjectName', ns)
            
            # Filter for files only
            if object_type != 'File' or not object_name:
                continue
            
            # Parse object name: (junction_path);/path/to/file
            junction_path, file_path = parse_object_name(object_name)
            
            # Extract SVM and filesystem from Computer element
            computer = system.find('ns:Computer', ns) or system.find('Computer')
            filesystem_id, svm_name = parse_computer(computer.text if computer is not None else '')
            
            # Extract timestamp
            time_created = system.find('ns:TimeCreated', ns) or system.find('TimeCreated')
            timestamp = time_created.get('SystemTime') if time_created is not None else ''
            
            event = {
                'file_path': file_path,
                'junction_path': junction_path,
                'svm_name': svm_name,
                'filesystem_id': filesystem_id,
                'operation': 'create',
                'timestamp': timestamp,
                'user': get_event_data_value(event_data, 'SubjectUserName', ns, 'unknown'),
                'user_ip': get_event_data_value(event_data, 'SubjectIP', ns, ''),
                'source_log': log_key,
                'format': 'xml',
                'event_id': event_id
            }
            event['dedup_id'] = generate_event_id(file_path, timestamp, log_key)
            events.append(event)
    
    except Exception as e:
        print(f"Error parsing XML: {e}")
        import traceback
        traceback.print_exc()
    
    return events


def parse_evtx_audit(content: bytes, log_key: str) -> List[Dict]:
    """Parse EVTX format audit log."""
    events = []
    
    if not EVTX_AVAILABLE:
        print("EVTX parser not available")
        return events
    
    # Write bytes to temp file (python-evtx requires file path)
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.evtx') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        with Evtx(temp_file_path) as evtx:
            for record in evtx.records():
                try:
                    # Parse XML from record
                    xml_str = record.xml()
                    root = ET.fromstring(xml_str)
                    
                    # NetApp ONTAP uses their own namespace
                    ns = {'evt': 'http://schemas.netapp.com/events/event'}
                    
                    # Get Event ID
                    event_id_elem = root.find('.//evt:EventID', ns)
                    
                    if event_id_elem is None:
                        continue
                    
                    event_id = event_id_elem.text
                    
                    # Filter for file creation (4656)
                    if event_id != '4656':
                        continue
                    
                    # Extract event data
                    event_data = {}
                    for data_elem in root.findall('.//evt:Data', ns):
                        name = data_elem.get('Name')
                        if name:
                            event_data[name] = data_elem.text or ''
                    
                    object_type = event_data.get('ObjectType', '')
                    object_name = event_data.get('ObjectName', '')
                    
                    # Filter for files only
                    if object_type != 'File' or not object_name:
                        continue
                    
                    # Parse object name
                    junction_path, file_path = parse_object_name(object_name)
                    
                    # Get computer/system info
                    computer_elem = root.find('.//evt:Computer', ns)
                    computer = computer_elem.text if computer_elem is not None else ''
                    filesystem_id, svm_name = parse_computer(computer)
                    
                    # Get timestamp
                    time_elem = root.find('.//evt:TimeCreated', ns)
                    timestamp = time_elem.get('SystemTime', '') if time_elem is not None else ''
                    
                    # Get user IP
                    user_ip = event_data.get('SubjectIP', '')
                    
                    event = {
                        'file_path': file_path,
                        'junction_path': junction_path,
                        'svm_name': svm_name,
                        'filesystem_id': filesystem_id,
                        'operation': 'create',
                        'timestamp': timestamp,
                        'user': event_data.get('SubjectUserName', 'unknown'),
                        'user_ip': user_ip,
                        'source_log': log_key,
                        'format': 'evtx',
                        'event_id': event_id
                    }
                    event['dedup_id'] = generate_event_id(file_path, timestamp, log_key)
                    events.append(event)
                    
                except Exception as e:
                    print(f"Error parsing EVTX record: {e}")
                    continue
    
    except Exception as e:
        print(f"Error parsing EVTX file: {e}")
    finally:
        # Clean up temp file
        if temp_file:
            try:
                import os
                os.unlink(temp_file_path)
            except:
                pass
    
    return events


def get_event_data_value(event_data, name: str, ns: dict, default: str = '') -> str:
    """Extract value from EventData by Name attribute with namespace support."""
    # Try with namespace first if namespace is defined
    if ns and 'ns' in ns:
        for data in event_data.findall('ns:Data', ns):
            if data.get('Name') == name:
                return data.text or default
    
    # Fallback without namespace
    for data in event_data.findall('Data'):
        if data.get('Name') == name:
            return data.text or default
    
    return default


def generate_event_id(file_path: str, timestamp: str, source_log: str) -> str:
    """Generate deterministic event ID for deduplication."""
    content = f"{file_path}|{timestamp}|{source_log}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def parse_object_name(object_name: str) -> tuple:
    """Parse ObjectName: (junction_path);/file/path -> (junction_path, file_path)"""
    import re
    match = re.match(r'\(([^)]+)\);(.+)', object_name)
    if match:
        return match.group(1), match.group(2)
    # Fallback: no junction path
    if ';' in object_name:
        return '', object_name.split(';', 1)[1]
    return '', object_name


def parse_computer(computer: str) -> tuple:
    """Parse Computer: FsxId.../svm_name -> (filesystem_id, svm_name)"""
    if '/' in computer:
        parts = computer.split('/', 1)
        return parts[0], parts[1]
    return computer, ''


def _send_to_sqs(queue_url: str, events: List[Dict]):
    """Send events to SQS queue in batches of 10."""
    for i in range(0, len(events), 10):
        batch = events[i:i+10]
        entries = [{'Id': str(j), 'MessageBody': json.dumps(e)} for j, e in enumerate(batch)]
        sqs_client.send_message_batch(QueueUrl=queue_url, Entries=entries)


def _send_to_sns(topic_arn: str, events: List[Dict]):
    """Send events to SNS topic."""
    for event in events:
        sns_client.publish(TopicArn=topic_arn, Message=json.dumps(event))


def _send_to_cloudwatch_logs(log_group: str, events: List[Dict]):
    """Send events to CloudWatch Logs."""
    log_stream = datetime.utcnow().strftime('%Y/%m/%d')
    try:
        logs_client.create_log_stream(logGroupName=log_group, logStreamName=log_stream)
    except logs_client.exceptions.ResourceAlreadyExistsException:
        pass
    log_events = [{'timestamp': int(datetime.utcnow().timestamp() * 1000), 'message': json.dumps(e)} for e in events]
    logs_client.put_log_events(logGroupName=log_group, logStreamName=log_stream, logEvents=log_events)


def _send_to_eventbridge(bus_name: str, events: List[Dict]):
    """Send events to EventBridge bus."""
    for i in range(0, len(events), 10):
        batch = events[i:i+10]
        entries = [
            {'Source': 'fsx.ontap.audit', 'DetailType': 'File Event', 'Detail': json.dumps(e), 'EventBusName': bus_name}
            for e in batch
        ]
        events_client.put_events(Entries=entries)


def _send_to_destination(dest_type: str, dest_arn: str, events: List[Dict]):
    """Route events to appropriate destination."""
    if dest_type == 'sqs':
        _send_to_sqs(dest_arn, events)
    elif dest_type == 'sns':
        _send_to_sns(dest_arn, events)
    elif dest_type == 'cloudwatch_logs':
        _send_to_cloudwatch_logs(dest_arn, events)
    elif dest_type == 'eventbridge':
        _send_to_eventbridge(dest_arn, events)


def publish_events(event_list: List[Dict]):
    """Publish events to configured destinations or default EventBridge."""
    if not event_list:
        return
    
    # Group events by destination
    routed: Dict[tuple, List[Dict]] = {}
    default_events = []
    
    for event in event_list:
        route = get_route(event.get('svm_name', ''), event.get('junction_path', ''))
        if route:
            dest_key = (route['destination_type'], route.get('destination_arn', ''))
            routed.setdefault(dest_key, []).append(event)
        else:
            default_events.append(event)
    
    # Send to configured destinations
    for (dest_type, dest_arn), events in routed.items():
        try:
            _send_to_destination(dest_type, dest_arn, events)
            print(f"Routed {len(events)} events to {dest_type}:{dest_arn}")
        except Exception as e:
            print(f"Error sending to {dest_type}:{dest_arn}: {e}")
    
    # Send unmatched to default EventBridge
    if default_events and EVENT_BUS_NAME:
        _send_to_eventbridge(EVENT_BUS_NAME, default_events)
        print(f"Sent {len(default_events)} events to default EventBridge")


def extract_filename(log_key: str) -> str:
    """Extract filename from S3 key."""
    return log_key.replace(f"{AUDIT_PREFIX}", '')
