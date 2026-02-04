# Data Models

## File Event

Represents a file operation detected from audit logs.

```python
{
    'file_path': str,      # Absolute path on FSx volume
    'operation': str,      # 'create' (only supported currently)
    'timestamp': str,      # ISO 8601 timestamp
    'user': str,           # Username or 'unknown'
    'user_ip': str,        # Client IP address
    'source_log': str,     # Audit log filename
    'format': str,         # 'xml' or 'evtx'
    'event_id': str        # ONTAP event ID (e.g., '4656')
}
```

---

## Checkpoint

Tracks processing progress in DynamoDB.

```python
{
    'pk': 'tracker',                    # Partition key (constant)
    'last_processed_log': str,          # Last processed log filename
    'last_check_time': str,             # ISO 8601 timestamp
    'processed_count': int              # Total logs processed
}
```

---

## Thumbnail Metadata

S3 object metadata for generated thumbnails.

```python
{
    'original-path': str,               # Source file path
    'thumbnail-size': '200x200',        # Thumbnail dimensions
    'generated-by': 'fsx-audit-processor'
}
```

---

## Supported Image Formats

```python
SUPPORTED_FORMATS = {
    '.jpg', '.jpeg', '.png', '.gif', 
    '.webp', '.bmp', '.tiff', '.tif'
}
```
