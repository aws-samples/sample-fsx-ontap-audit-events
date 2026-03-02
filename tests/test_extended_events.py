"""
Unit tests for extended event type monitoring (delete, modify, read).
"""

import pytest
import json
from unittest.mock import patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'audit_processor'))

import index


class TestEventTypeFiltering:
    """Test event type configuration and filtering."""

    def test_should_process_create_enabled(self):
        """Test create event processing when enabled."""
        index._event_types['create'] = True
        should_process, operation = index.should_process_event('4656')
        assert should_process is True
        assert operation == 'create'

    def test_should_process_create_disabled(self):
        """Test create event skipped when disabled."""
        index._event_types['create'] = False
        should_process, operation = index.should_process_event('4656')
        assert should_process is False
        assert operation == ''

    def test_should_process_delete_enabled(self):
        """Test delete event processing when enabled."""
        index._event_types['delete'] = True
        should_process, operation = index.should_process_event('4660')
        assert should_process is True
        assert operation == 'delete'

    def test_should_process_delete_disabled(self):
        """Test delete event skipped when disabled."""
        index._event_types['delete'] = False
        should_process, operation = index.should_process_event('4660')
        assert should_process is False

    def test_should_process_modify_with_write_access(self):
        """Test modify event detected from 4663 with WRITE_DATA."""
        index._event_types['modify'] = True
        should_process, operation = index.should_process_event('4663', 'WRITE_DATA')
        assert should_process is True
        assert operation == 'modify'

    def test_should_process_modify_with_append_access(self):
        """Test modify event detected from 4663 with APPEND_DATA."""
        index._event_types['modify'] = True
        should_process, operation = index.should_process_event('4663', 'APPEND_DATA')
        assert should_process is True
        assert operation == 'modify'

    def test_should_process_read_with_read_access(self):
        """Test read event detected from 4663 with READ_DATA."""
        index._event_types['read'] = True
        should_process, operation = index.should_process_event('4663', 'READ_DATA')
        assert should_process is True
        assert operation == 'read'

    def test_should_process_modify_disabled(self):
        """Test modify event skipped when disabled."""
        index._event_types['modify'] = False
        should_process, operation = index.should_process_event('4663', 'WRITE_DATA')
        assert should_process is False

    def test_should_process_read_disabled(self):
        """Test read event skipped when disabled."""
        index._event_types['read'] = False
        should_process, operation = index.should_process_event('4663', 'READ_DATA')
        assert should_process is False

    def test_should_process_unknown_event_id(self):
        """Test unknown event ID is skipped."""
        should_process, operation = index.should_process_event('9999')
        assert should_process is False


class TestDeleteEventParsing:
    """Test parsing of delete events (Event ID 4660)."""

    def test_parse_delete_event_xml(self):
        """Test parsing Event ID 4660 (delete) from XML."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4660</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:00:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/deleted.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
      <Data Name="SubjectIP">172.31.2.69</Data>
    </EventData>
  </Event>
</Events>'''
        
        # Enable delete events
        index._event_types['delete'] = True
        index._event_types['create'] = False
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 1
        assert events[0]['operation'] == 'delete'
        assert events[0]['file_path'] == '/data/deleted.txt'
        assert events[0]['event_id'] == '4660'


class TestModifyEventParsing:
    """Test parsing of modify events (Event ID 4663 with WRITE)."""

    def test_parse_modify_event_xml(self):
        """Test parsing Event ID 4663 (modify) from XML."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4663</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:00:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/modified.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
      <Data Name="SubjectIP">172.31.2.69</Data>
      <Data Name="AccessMask">WRITE_DATA</Data>
    </EventData>
  </Event>
</Events>'''
        
        # Enable modify events
        index._event_types['modify'] = True
        index._event_types['create'] = False
        index._event_types['delete'] = False
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 1
        assert events[0]['operation'] == 'modify'
        assert events[0]['file_path'] == '/data/modified.txt'
        assert events[0]['event_id'] == '4663'

    def test_parse_modify_skipped_when_disabled(self):
        """Test modify event skipped when disabled."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4663</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/modified.txt</Data>
      <Data Name="AccessMask">WRITE_DATA</Data>
    </EventData>
  </Event>
</Events>'''
        
        # Disable modify events
        index._event_types['modify'] = False
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 0


class TestReadEventParsing:
    """Test parsing of read events (Event ID 4663 with READ)."""

    def test_parse_read_event_xml(self):
        """Test parsing Event ID 4663 (read) from XML."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4663</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:00:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/read.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
      <Data Name="SubjectIP">172.31.2.69</Data>
      <Data Name="AccessMask">READ_DATA</Data>
    </EventData>
  </Event>
</Events>'''
        
        # Enable read events
        index._event_types['read'] = True
        index._event_types['create'] = False
        index._event_types['delete'] = False
        index._event_types['modify'] = False
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 1
        assert events[0]['operation'] == 'read'
        assert events[0]['file_path'] == '/data/read.txt'
        assert events[0]['event_id'] == '4663'


class TestMultipleEventTypes:
    """Test processing multiple event types in same log."""

    def test_parse_mixed_events(self):
        """Test parsing create, delete, and modify in same log."""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Events>
  <Event>
    <System>
      <EventID>4656</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:00:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/created.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
    </EventData>
  </Event>
  <Event>
    <System>
      <EventID>4660</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:01:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/deleted.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
    </EventData>
  </Event>
  <Event>
    <System>
      <EventID>4663</EventID>
      <Computer>FsxId0a60f59a70d0b2b4a.fsxz_s01</Computer>
      <TimeCreated SystemTime="2026-02-19T02:02:00.000000000Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/data/modified.txt</Data>
      <Data Name="SubjectUserName">user1</Data>
      <Data Name="AccessMask">WRITE_DATA</Data>
    </EventData>
  </Event>
</Events>'''
        
        # Enable all event types
        index._event_types['create'] = True
        index._event_types['delete'] = True
        index._event_types['modify'] = True
        
        events = index.parse_xml_audit(xml_content.encode(), 'test.xml')
        
        assert len(events) == 3
        assert events[0]['operation'] == 'create'
        assert events[1]['operation'] == 'delete'
        assert events[2]['operation'] == 'modify'


class TestDedupIdGeneration:
    """Test dedup ID includes operation type."""

    def test_dedup_id_different_for_operations(self):
        """Test same file with different operations has different dedup IDs."""
        file_path = '/data/test.txt'
        timestamp = '2026-02-19T02:00:00Z'
        log_key = 'test.xml'
        
        create_id = index.generate_event_id(file_path, timestamp, log_key, 'create')
        delete_id = index.generate_event_id(file_path, timestamp, log_key, 'delete')
        modify_id = index.generate_event_id(file_path, timestamp, log_key, 'modify')
        
        assert create_id != delete_id
        assert create_id != modify_id
        assert delete_id != modify_id

    def test_dedup_id_same_for_same_operation(self):
        """Test same file with same operation has same dedup ID."""
        file_path = '/data/test.txt'
        timestamp = '2026-02-19T02:00:00Z'
        log_key = 'test.xml'
        
        id1 = index.generate_event_id(file_path, timestamp, log_key, 'create')
        id2 = index.generate_event_id(file_path, timestamp, log_key, 'create')
        
        assert id1 == id2
