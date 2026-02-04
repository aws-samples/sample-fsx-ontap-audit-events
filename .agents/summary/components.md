# Components

## Lambda Functions

### Audit Processor (`lambda/audit_processor/index.py`)
**Purpose**: Parses ONTAP audit logs and extracts file creation events.

**Key Functions**:
| Function | Description |
|----------|-------------|
| `lambda_handler` | Main entry point, orchestrates processing |
| `get_checkpoint` | Reads last processed log from DynamoDB |
| `update_checkpoint` | Saves processing progress |
| `initialize_checkpoint_to_latest` | First-run: skips to latest log |
| `list_new_logs` | Lists audit logs after checkpoint |
| `identify_active_log` | Detects currently-written log file |
| `process_audit_log` | Downloads and parses single log |
| `parse_xml_audit` | Parses XML format audit logs |
| `parse_evtx_audit` | Parses EVTX format audit logs |
| `send_to_sqs_batch` | Sends events to SQS in batches of 10 |

**Environment Variables**:
- `BUCKET` - S3 Access Point alias for audit logs
- `AUDIT_PREFIX` - Path prefix for audit logs
- `TABLE_NAME` - DynamoDB table name
- `QUEUE_URL` - SQS queue URL
- `MAX_KEYS` - Max logs per invocation (default: 100)

---

### File Processor (`lambda/file_processor/index.py`)
**Purpose**: Generates thumbnails for image files.

**Key Functions**:
| Function | Description |
|----------|-------------|
| `lambda_handler` | Processes SQS batch of file events |
| `process_file_event` | Handles single file event |
| `generate_thumbnail` | Creates 200x200 JPEG thumbnail |

**Environment Variables**:
- `S3_ACCESS_POINT_ALIAS` - Input volume access point
- `OUTPUT_S3_ACCESS_POINT_ALIAS` - Output volume access point

**Supported Formats**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.bmp`, `.tiff`, `.tif`

---

## Lambda Layers

### EVTX Layer (`layers/evtx/`)
- **Package**: python-evtx
- **Purpose**: Parse Windows Event Log (EVTX) format

### Pillow Layer (`layers/pillow/`)
- **Package**: Pillow
- **Purpose**: Image processing and thumbnail generation

---

## Infrastructure (`infra/fsx_audit_stack.py`)

### Resources Created
| Resource | Type | Purpose |
|----------|------|---------|
| AuditLogStateTable | DynamoDB Table | Checkpoint storage |
| FileEventsQueue | SQS Queue | Event buffering |
| FileEventsDLQ | SQS Queue | Dead letter queue |
| AuditLogProcessor | Lambda Function | Audit parsing |
| FileProcessor | Lambda Function | Thumbnail generation |
| AuditProcessorSchedule | EventBridge Rule | 1-minute trigger |
| EvtxLayer | Lambda Layer | EVTX parsing |
| PillowLayer | Lambda Layer | Image processing |

### CDK Context Parameters
| Parameter | Description |
|-----------|-------------|
| `audit_s3_access_point_name` | Audit AP name (for IAM) |
| `audit_s3_access_point_alias` | Audit AP alias (for API calls) |
| `file_s3_access_point_name` | File AP name (for IAM) |
| `file_s3_access_point_alias` | File AP alias (for API calls) |
| `output_s3_access_point_name` | Output AP name (for IAM) |
| `output_s3_access_point_alias` | Output AP alias (for API calls) |
