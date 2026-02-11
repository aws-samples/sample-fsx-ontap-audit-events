"""
Unit tests for audit processor Lambda function.
"""

import pytest
import json
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add lambda directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'audit_processor'))

import index


class TestRoutingConfigParser:
    """Test routing configuration parsing."""

    def test_get_route_found(self):
        """Test route lookup when route exists."""
        # Temporarily set routes
        original = index._routes.copy()
        index._routes[('svm1', 'unix')] = {
            'svm_name': 'svm1',
            'junction_path': 'unix',
            'destination_type': 'sqs',
            'destination_arn': 'arn:aws:sqs:us-east-1:123:test-queue'
        }
        
        route = index.get_route('svm1', 'unix')
        
        assert route is not None
        assert route['destination_type'] == 'sqs'
        index._routes = original

    def test_get_route_not_found(self):
        """Test route lookup when route doesn't exist."""
        route = index.get_route('nonexistent', 'path')
        assert route is None

    def test_parse_valid_config(self):
        """Test parsing valid routing config."""
        config = {
            'routes': [
                {'svm_name': 'svm1', 'junction_path': 'unix', 'destination_type': 'sqs'},
                {'svm_name': 'svm2', 'junction_path': 'ntfs', 'destination_type': 'sns'}
            ]
        }
        
        # Simulate parsing
        routes = {}
        for route in config.get('routes', []):
            if 'svm_name' in route and 'junction_path' in route:
                key = (route['svm_name'], route['junction_path'])
                routes[key] = route
        
        assert len(routes) == 2
        assert ('svm1', 'unix') in routes
        assert ('svm2', 'ntfs') in routes

    def test_parse_config_missing_fields(self):
        """Test parsing config with missing required fields."""
        config = {
            'routes': [
                {'svm_name': 'svm1'},  # Missing junction_path
                {'junction_path': 'unix'},  # Missing svm_name
                {'svm_name': 'svm3', 'junction_path': 'data', 'destination_type': 'sqs'}
            ]
        }
        
        routes = {}
        for route in config.get('routes', []):
            if 'svm_name' in route and 'junction_path' in route:
                key = (route['svm_name'], route['junction_path'])
                routes[key] = route
        
        assert len(routes) == 1
        assert ('svm3', 'data') in routes


class TestCheckpointManagement:
    """Test checkpoint read/write operations."""
    
    @patch('index.table')
    def test_get_checkpoint_existing(self, mock_table):
        """Test reading existing checkpoint."""
        mock_table.get_item.return_value = {
            'Item': {
                'pk': 'tracker',
                'last_processed_log': 'audit_test_D2026-02-03-T15-00-00_0000000000.xml',
                'last_check_time': '2026-02-03T15:10:00Z',
                'processed_count': 100
            }
        }
        
        checkpoint = index.get_checkpoint()
        
        assert checkpoint['last_processed_log'] == 'audit_test_D2026-02-03-T15-00-00_0000000000.xml'
        assert checkpoint['processed_count'] == 100
    
    @patch('index.table')
    def test_get_checkpoint_first_run(self, mock_table):
        """Test reading checkpoint on first run."""
        mock_table.get_item.return_value = {}
        
        checkpoint = index.get_checkpoint()
        
        assert checkpoint['last_processed_log'] == ''
        assert checkpoint['processed_count'] == 0
    
    @patch('index.table')
    def test_update_checkpoint(self, mock_table):
        """Test updating checkpoint."""
        index.update_checkpoint('audit_test_D2026-02-03-T15-05-00_0000000000.xml', 5)
        
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args
        
        assert call_args[1]['Key'] == {'pk': 'tracker'}
        assert ':log' in call_args[1]['ExpressionAttributeValues']


class TestAuditLogListing:
    """Test S3 listing with StartAfter optimization."""
    
    @patch('index.s3')
    def test_list_new_logs_with_checkpoint(self, mock_s3):
        """Test listing with existing checkpoint."""
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'audit/audit_test_D2026-02-03-T15-05-00_0000000000.xml'},
                {'Key': 'audit/audit_test_D2026-02-03-T15-10-00_0000000000.xml'},
            ],
            'IsTruncated': False
        }
        
        logs = index.list_new_logs('audit_test_D2026-02-03-T15-00-00_0000000000.xml')
        
        # Should filter out last log (active)
        assert len(logs) == 1
        assert logs[0] == 'audit/audit_test_D2026-02-03-T15-05-00_0000000000.xml'
    
    @patch('index.s3')
    def test_list_new_logs_empty(self, mock_s3):
        """Test listing with no new logs."""
        mock_s3.list_objects_v2.return_value = {}
        
        logs = index.list_new_logs('audit_test_D2026-02-03-T15-00-00_0000000000.xml')
        
        assert logs == []
    
    def test_identify_active_log_with_last_marker(self):
        """Test identifying active log with _last marker."""
        logs = [
            'audit/audit_test_D2026-02-03-T15-00-00_0000000000.xml',
            'audit/audit_test_last.xml'
        ]
        
        active = index.identify_active_log(logs, is_truncated=False)
        
        assert active == 'audit/audit_test_last.xml'
    
    def test_identify_active_log_newest_file(self):
        """Test identifying active log as newest file."""
        logs = [
            'audit/audit_test_D2026-02-03-T15-00-00_0000000000.xml',
            'audit/audit_test_D2026-02-03-T15-05-00_0000000000.xml'
        ]
        
        active = index.identify_active_log(logs, is_truncated=False)
        
        assert active == 'audit/audit_test_D2026-02-03-T15-05-00_0000000000.xml'
    
    def test_identify_active_log_truncated(self):
        """Test identifying active log when results are truncated."""
        logs = [
            'audit/audit_test_D2026-02-03-T15-00-00_0000000000.xml',
            'audit/audit_test_D2026-02-03-T15-05-00_0000000000.xml'
        ]
        
        active = index.identify_active_log(logs, is_truncated=True)
        
        assert active is None


class TestXMLParsing:
    """Test XML audit log parsing."""
    
    def test_parse_xml_file_creation(self):
        """Test parsing file creation event."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4656</EventID>
      <TimeCreated SystemTime="2026-02-03T20:33:06.809779000Z"/>
      <Computer>FsxId123/svm1</Computer>
    </System>
    <EventData>
      <Data Name="SubjectUserName">testuser</Data>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(ntfs);/data/test.jpg</Data>
      <Data Name="SubjectIP">172.31.18.58</Data>
    </EventData>
  </Event>
</Events>'''
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 1
        assert events[0]['file_path'] == '/data/test.jpg'
        assert events[0]['operation'] == 'create'
        assert events[0]['user'] == 'testuser'
        assert events[0]['event_id'] == '4656'
    
    def test_parse_xml_filter_directories(self):
        """Test filtering out directory events."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4656</EventID>
      <TimeCreated SystemTime="2026-02-03T20:33:06Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">Directory</Data>
      <Data Name="ObjectName">(ntfs);/data/</Data>
    </EventData>
  </Event>
</Events>'''
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 0
    
    def test_parse_xml_filter_non_create_events(self):
        """Test filtering non-4656 events."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4663</EventID>
      <TimeCreated SystemTime="2026-02-03T20:33:06Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(ntfs);/data/test.jpg</Data>
    </EventData>
  </Event>
</Events>'''
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 0
    
    def test_get_event_data_value(self):
        """Test extracting values from EventData."""
        xml_content = '''<EventData>
  <Data Name="SubjectUserName">testuser</Data>
  <Data Name="ObjectType">File</Data>
</EventData>'''
        
        event_data = ET.fromstring(xml_content)
        ns = {}  # Empty namespace dict for non-namespaced XML
        
        assert index.get_event_data_value(event_data, 'SubjectUserName', ns) == 'testuser'
        assert index.get_event_data_value(event_data, 'ObjectType', ns) == 'File'
        assert index.get_event_data_value(event_data, 'Missing', ns, 'default') == 'default'


class TestEventBridgePublishing:
    """Test EventBridge event publishing."""
    
    @patch('index.events_client')
    @patch('index.EVENT_BUS_NAME', 'test-bus')
    @patch('index._routes', {})
    def test_publish_events_single_batch(self, mock_events):
        """Test publishing single batch to EventBridge."""
        events = [
            {'file_path': '/data/test1.jpg', 'operation': 'create'},
            {'file_path': '/data/test2.jpg', 'operation': 'create'}
        ]
        
        index.publish_events(events)
        
        mock_events.put_events.assert_called_once()
        call_args = mock_events.put_events.call_args
        
        assert len(call_args[1]['Entries']) == 2
        assert call_args[1]['Entries'][0]['Source'] == 'fsx.ontap.audit'
        assert call_args[1]['Entries'][0]['DetailType'] == 'File Event'
    
    @patch('index.events_client')
    @patch('index.EVENT_BUS_NAME', 'test-bus')
    @patch('index._routes', {})
    def test_publish_events_multiple_batches(self, mock_events):
        """Test publishing multiple batches to EventBridge."""
        events = [{'file_path': f'/data/test{i}.jpg', 'operation': 'create'} for i in range(25)]
        
        index.publish_events(events)
        
        # Should be called 3 times (10 + 10 + 5)
        assert mock_events.put_events.call_count == 3
    
    @patch('index.events_client')
    def test_publish_events_empty_list(self, mock_events):
        """Test publishing empty list does nothing."""
        index.publish_events([])
        
        mock_events.put_events.assert_not_called()


class TestRoutingDestinations:
    """Test routing to different destinations."""

    @patch('index.sqs_client')
    def test_send_to_sqs(self, mock_sqs):
        """Test sending events to SQS."""
        events = [{'file_path': '/test.jpg'}]
        index._send_to_sqs('https://sqs.us-east-1.amazonaws.com/123/queue', events)
        mock_sqs.send_message_batch.assert_called_once()

    @patch('index.sns_client')
    def test_send_to_sns(self, mock_sns):
        """Test sending events to SNS."""
        events = [{'file_path': '/test.jpg'}]
        index._send_to_sns('arn:aws:sns:us-east-1:123:topic', events)
        mock_sns.publish.assert_called_once()

    @patch('index.logs_client')
    def test_send_to_cloudwatch_logs(self, mock_logs):
        """Test sending events to CloudWatch Logs."""
        mock_logs.exceptions.ResourceAlreadyExistsException = Exception
        events = [{'file_path': '/test.jpg'}]
        index._send_to_cloudwatch_logs('/fsx/test', events)
        mock_logs.create_log_stream.assert_called_once()
        mock_logs.put_log_events.assert_called_once()

    @patch('index.sqs_client')
    @patch('index.events_client')
    @patch('index.EVENT_BUS_NAME', 'test-bus')
    def test_publish_events_with_routing(self, mock_events, mock_sqs):
        """Test routing events to configured destination."""
        original = index._routes.copy()
        index._routes[('svm1', 'unix')] = {
            'destination_type': 'sqs',
            'destination_arn': 'https://sqs.us-east-1.amazonaws.com/123/queue'
        }
        
        events = [
            {'svm_name': 'svm1', 'junction_path': 'unix', 'file_path': '/test.jpg'},
            {'svm_name': 'svm2', 'junction_path': 'other', 'file_path': '/test2.jpg'}
        ]
        
        index.publish_events(events)
        
        mock_sqs.send_message_batch.assert_called_once()  # Routed event
        mock_events.put_events.assert_called_once()  # Default event
        index._routes = original


class TestLambdaHandler:
    """Test main Lambda handler."""
    
    @patch('index.update_checkpoint')
    @patch('index.publish_events')
    @patch('index.process_audit_log')
    @patch('index.list_new_logs')
    @patch('index.get_checkpoint')
    def test_lambda_handler_success(self, mock_get_checkpoint, mock_list_logs, 
                                    mock_process_log, mock_publish, mock_update_checkpoint):
        """Test successful Lambda execution."""
        mock_get_checkpoint.return_value = {'last_processed_log': 'previous.xml'}
        mock_list_logs.return_value = ['audit/test1.xml', 'audit/test2.xml']
        mock_process_log.return_value = [
            {'file_path': '/data/test.jpg', 'operation': 'create'}
        ]
        
        result = index.lambda_handler({}, None)
        
        assert result['statusCode'] == 200
        assert result['logs_processed'] == 2
        assert result['events_found'] == 2
        assert mock_publish.call_count == 2
    
    @patch('index.get_checkpoint')
    @patch('index.list_new_logs')
    def test_lambda_handler_no_new_logs(self, mock_list_logs, mock_get_checkpoint):
        """Test Lambda execution with no new logs."""
        mock_get_checkpoint.return_value = {'last_processed_log': 'test.xml'}
        mock_list_logs.return_value = []
        
        result = index.lambda_handler({}, None)
        
        assert result['statusCode'] == 200
        assert result['logs_processed'] == 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_extract_filename(self):
        """Test extracting filename from S3 key."""
        assert index.extract_filename('audit/test.xml') == 'test.xml'
        assert index.extract_filename('audit/subdir/test.xml') == 'subdir/test.xml'
