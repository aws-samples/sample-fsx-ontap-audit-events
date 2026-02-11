# Interfaces and APIs

## Event Schema

### File Event (Published to EventBridge/SQS/SNS)

```json
{
  "file_path": "/images/photo.jpg",
  "junction_path": "unix",
  "svm_name": "fsxz_s01",
  "filesystem_id": "FsxId0a60f59a70d0b2b4a",
  "operation": "create",
  "timestamp": "2026-02-09T20:32:20.359509000Z",
  "user": "Administrator",
  "user_ip": "172.31.2.69",
  "source_log": "audit/audit_svm_log.0000000001.xml",
  "format": "xml",
  "event_id": "4656",
  "dedup_id": "a1b2c3d4e5f67890"
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Full path to file within volume |
| `junction_path` | string | Volume junction path (identifies volume) |
| `svm_name` | string | Storage Virtual Machine name |
| `filesystem_id` | string | FSx filesystem ID |
| `operation` | string | Operation type (currently "create") |
| `timestamp` | string | ISO 8601 timestamp from audit log |
| `user` | string | Username who performed operation |
| `user_ip` | string | Client IP address |
| `source_log` | string | S3 key of source audit log |
| `format` | string | Log format ("xml" or "evtx") |
| `event_id` | string | Windows event ID (4656 = create) |
| `dedup_id` | string | Deterministic ID for deduplication |

## EventBridge Integration

### Event Structure
```json
{
  "Source": "fsx.ontap.audit",
  "DetailType": "File Event",
  "Detail": { /* File Event JSON */ },
  "EventBusName": "FsxAuditStack-file-events"
}
```

### Example EventBridge Rule (Route by Junction Path)
```json
{
  "source": ["fsx.ontap.audit"],
  "detail-type": ["File Event"],
  "detail": {
    "junction_path": ["unix"]
  }
}
```

### Example EventBridge Rule (Route by File Extension)
```json
{
  "source": ["fsx.ontap.audit"],
  "detail-type": ["File Event"],
  "detail": {
    "file_path": [{"suffix": ".jpg"}, {"suffix": ".png"}]
  }
}
```

## DynamoDB Schema

### Checkpoint Table

| Attribute | Type | Description |
|-----------|------|-------------|
| `pk` | String (PK) | Always "tracker" |
| `last_processed_log` | String | Filename of last processed log |
| `last_check_time` | String | ISO timestamp of last update |
| `processed_count` | Number | Running total of logs processed |

## S3 Access Point Interface

### Audit Log Access
- **Bucket**: S3 Access Point alias (e.g., `audit-ap-abc123-s3alias`)
- **Prefix**: Configurable (default: `audit/`)
- **Operations**: `ListObjectsV2`, `GetObject`

### File Data Access
- **Bucket**: S3 Access Point alias for data volume
- **Operations**: `GetObject`, `PutObject`

## CDK Stack Parameters

```python
FsxAuditStack(
    app,
    "FsxAuditStack",
    audit_s3_access_point_name="audit-ap",      # For IAM ARN
    audit_s3_access_point_alias="audit-alias",  # For API calls
    file_s3_access_point_name="file-ap",
    file_s3_access_point_alias="file-alias",
    output_s3_access_point_name="output-ap",
    output_s3_access_point_alias="output-alias",
    audit_prefix="svm1/audit/",
    lambda_path="../lambda",
    layers_path="../layers",
)
```
