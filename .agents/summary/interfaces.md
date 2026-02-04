# Interfaces

## S3 Access Points

### Audit Access Point
- **Usage**: Read audit logs from FSx ONTAP
- **Operations**: `ListObjectsV2`, `GetObject`
- **Path Pattern**: `audit_<svm>_D<timestamp>_<sequence>.xml`

### File Access Point  
- **Usage**: Read original files for processing
- **Operations**: `GetObject`

### Output Access Point
- **Usage**: Write processed files (thumbnails)
- **Operations**: `PutObject`
- **Path Pattern**: `/thumbnails/<original_path>`

---

## SQS Message Format

```json
{
  "file_path": "/path/to/file.png",
  "operation": "create",
  "timestamp": "2026-02-04T00:23:17.559509000Z",
  "user": "unknown",
  "user_ip": "10.0.0.1",
  "source_log": "audit_fsxz_s01_D2026-02-04-T00-25-06_0000000000.xml",
  "format": "xml",
  "event_id": "4656"
}
```

---

## DynamoDB Schema

### Checkpoint Table
| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String | Partition key, always "tracker" |
| `last_processed_log` | String | Filename of last processed log |
| `last_check_time` | String | ISO timestamp of last check |
| `processed_count` | Number | Total logs processed |

---

## ONTAP Audit Log Format (XML)

```xml
<Events xmlns="http://www.netapp.com/schemas/ONTAP/2007/AuditLog">
  <Event>
    <System>
      <EventID>4656</EventID>
      <TimeCreated SystemTime="2026-02-04T00:23:17Z"/>
    </System>
    <EventData>
      <Data Name="ObjectType">File</Data>
      <Data Name="ObjectName">(unix);/path/to/file.png</Data>
      <Data Name="SubjectIP" IPVersion="4">10.0.0.1</Data>
    </EventData>
  </Event>
</Events>
```

### Event IDs
| ID | Description |
|----|-------------|
| 4656 | File/Directory Create |

---

## Lambda Event Formats

### Audit Processor (EventBridge)
```json
{
  "version": "0",
  "source": "aws.events",
  "detail-type": "Scheduled Event"
}
```

### File Processor (SQS)
```json
{
  "Records": [
    {
      "body": "{\"file_path\": \"/test.png\", \"operation\": \"create\", ...}"
    }
  ]
}
```
