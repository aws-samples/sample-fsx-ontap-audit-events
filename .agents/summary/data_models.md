# Data Models

## Audit Log Formats

### XML Format (ONTAP Native)

```xml
<Events xmlns="http://www.netapp.com/schemas/ONTAP/2007/AuditLog">
  <Event>
    <System>
      <Provider Name="NetApp-Security-Auditing" Guid="{...}"/>
      <EventID>4656</EventID>
      <EventName>Open Object</EventName>
      <Source>NFSv4</Source>
      <TimeCreated SystemTime="2026-02-09T20:32:20.359509000Z"/>
      <Computer>FsxId0a60f59a70d0b2b4a/fsxz_s01</Computer>
      <ComputerUUID>uuid1/uuid2</ComputerUUID>
    </System>
    <EventData>
      <Data Name="SubjectIP" IPVersion="4">172.31.2.69</Data>
      <Data Name="SubjectUnix" Uid="1000" Gid="1000" Local="false"/>
      <Data Name="SubjectUserName">user1</Data>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/images/photo.jpg</Data>
    </EventData>
  </Event>
</Events>
```

### Key XML Elements

| Element | Path | Description |
|---------|------|-------------|
| EventID | `System/EventID` | Windows event type (4656=create) |
| Computer | `System/Computer` | `{filesystem_id}/{svm_name}` |
| TimeCreated | `System/TimeCreated@SystemTime` | Event timestamp |
| ObjectName | `EventData/Data[@Name='ObjectName']` | `({junction_path});{file_path}` |
| ObjectType | `EventData/Data[@Name='ObjectType']` | "File" or "Directory" |
| SubjectIP | `EventData/Data[@Name='SubjectIP']` | Client IP address |
| SubjectUserName | `EventData/Data[@Name='SubjectUserName']` | Username |

### EVTX Format (Windows Event Log)

Binary format parsed using `python-evtx` library. Contains same logical structure as XML but in Windows Event Log binary format.

## DynamoDB Checkpoint Record

```json
{
  "pk": "tracker",
  "last_processed_log": "audit_svm_log.0000000012.xml",
  "last_check_time": "2026-02-09T21:00:00.000000",
  "processed_count": 150
}
```

## Internal Event Structure

```python
{
    'file_path': str,        # /path/to/file.ext
    'junction_path': str,    # Volume junction (e.g., "unix", "ntfs_ap")
    'svm_name': str,         # SVM name (e.g., "fsxz_s01")
    'filesystem_id': str,    # FSx ID (e.g., "FsxId0a60f59a70d0b2b4a")
    'operation': str,        # "create" (currently only supported)
    'timestamp': str,        # ISO 8601 from audit log
    'user': str,             # Username or "unknown"
    'user_ip': str,          # Client IP or empty
    'source_log': str,       # S3 key of source log
    'format': str,           # "xml" or "evtx"
    'event_id': str,         # Windows event ID
    'dedup_id': str,         # SHA256 hash for deduplication
}
```

## ObjectName Parsing

The `ObjectName` field format varies by protocol:

| Protocol | Format | Example |
|----------|--------|---------|
| NFS | `(junction_path);/file/path` | `(unix);/images/photo.jpg` |
| SMB/CIFS | `(junction_path);/file/path` | `(ntfs_ap);/docs/report.docx` |

Parsing logic:
```python
# Input: "(unix);/images/photo.jpg"
# Output: junction_path="unix", file_path="/images/photo.jpg"
match = re.match(r'\(([^)]+)\);(.+)', object_name)
junction_path = match.group(1)  # "unix"
file_path = match.group(2)      # "/images/photo.jpg"
```

## Computer Field Parsing

```python
# Input: "FsxId0a60f59a70d0b2b4a/fsxz_s01"
# Output: filesystem_id="FsxId0a60f59a70d0b2b4a", svm_name="fsxz_s01"
parts = computer.split('/', 1)
filesystem_id = parts[0]
svm_name = parts[1]
```
