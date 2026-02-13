# AGENTS.md - AI Assistant Guide

> This file provides context for AI coding assistants working on this codebase.

## Project Overview

**FSx ONTAP Audit Event Processing** - Event-driven serverless application that monitors FSx ONTAP audit logs and publishes file events to configurable destinations (EventBridge, SQS, SNS, CloudWatch Logs).

**Primary Use Case**: Detect file operations on FSx ONTAP volumes accessed via NFS/SMB and trigger downstream processing.

## Directory Structure

```
audits/
├── infra/                    # CDK infrastructure (deploy from here)
│   ├── app.py               # CDK app entry point
│   ├── fsx_audit_stack.py   # Stack definition  
│   └── cdk.json             # CDK config with context params
├── lambda/                   # Lambda function code
│   ├── audit_processor/     # Core: parses audit logs, publishes events
│   │   └── index.py         # Main handler (~500 LOC)
│   └── file_processor/      # Example: generates thumbnails
│       └── index.py         # Example consumer (~180 LOC)
├── layers/                   # Lambda layers (pre-built)
│   ├── evtx/                # python-evtx for EVTX parsing
│   └── pillow/              # Pillow for image processing (example only)
├── scripts/                  # Build scripts
│   ├── build_evtx_layer.sh
│   └── build_pillow_layer.sh
├── tests/                    # Unit & integration tests
└── .agents/summary/          # Detailed documentation
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Audit Processor | `lambda/audit_processor/index.py` | Parse ONTAP audit logs, publish file events |
| File Processor | `lambda/file_processor/index.py` | Example: Generate thumbnails (optional) |
| CDK Stack | `infra/fsx_audit_stack.py` | AWS infrastructure definition |

## Event Schema

Events published to EventBridge/SQS/SNS:
```json
{
  "file_path": "/images/photo.jpg",
  "junction_path": "unix",
  "svm_name": "fsxz_s01",
  "filesystem_id": "FsxId0a60f59a70d0b2b4a",
  "operation": "create",
  "timestamp": "2026-02-09T20:32:20.359509000Z",
  "user": "user1",
  "user_ip": "172.31.2.69",
  "dedup_id": "a1b2c3d4e5f67890"
}
```

**Key Fields**:
- `junction_path`: Identifies the volume (use for EventBridge routing)
- `svm_name`: Storage Virtual Machine name
- `filesystem_id`: FSx filesystem ID
- `dedup_id`: Deterministic hash for deduplication

## Coding Patterns

### Lambda Handler Pattern
```python
def lambda_handler(event, context):
    """Main entry point."""
    # 1. Get checkpoint from DynamoDB
    # 2. List and process new logs
    # 3. Publish events to destinations
    # 4. Update checkpoint per-log (at-least-once)
    return {'statusCode': 200, 'logs_processed': n}
```

### XML Namespace Handling
```python
# Always use explicit None checks, not 'or' operator
element = parent.find('ns:Child', ns)
if element is None:
    element = parent.find('Child')
```

### ObjectName Parsing
```python
# Input: "(unix);/images/photo.jpg"
# Output: junction_path="unix", file_path="/images/photo.jpg"
def parse_object_name(object_name: str) -> tuple:
    match = re.match(r'\(([^)]+)\);(.+)', object_name)
    if match:
        return match.group(1), match.group(2)
    return '', object_name
```

### Environment Variables
All config externalized:
- `BUCKET`: S3 Access Point alias
- `TABLE_NAME`: DynamoDB checkpoint table
- `EVENT_BUS_NAME`: EventBridge bus (primary destination)
- `QUEUE_URL`, `SNS_TOPIC_ARN`, `LOG_GROUP_NAME`: Optional destinations

## Testing

```bash
source .venv/bin/activate
pytest tests/ -v

# Specific test file
pytest tests/test_audit_processor.py -v

# With coverage
pytest tests/ --cov=lambda --cov-report=html
```

### Test Files
- `test_audit_processor.py` - Audit parsing, checkpoint, event publishing
- `test_file_processor.py` - Thumbnail generation (example)
- `test_infrastructure_stack.py` - CDK stack validation
- `test_iam_configuration.py` - IAM policy tests
- `integration_test.py` - End-to-end tests

## Deployment

```bash
cd infra
source ../.venv/bin/activate
cdk deploy \
  -c audit_s3_access_point_name=<name> \
  -c audit_s3_access_point_alias=<alias> \
  -c file_s3_access_point_name=<name> \
  -c file_s3_access_point_alias=<alias>
```

## Important Implementation Details

### Checkpoint Mechanism
- DynamoDB stores `last_processed_log` filename
- Updated after EACH log (not batch) for at-least-once delivery
- On failure, processing stops to prevent gaps

### First-Run Behavior
`initialize_checkpoint_to_latest()` skips to latest log to avoid backlog processing.

### Active Log Detection
Files matching `*_last.xml` or `*_last.evtx` are skipped (actively being written).

### Event Routing via EventBridge
Create rules filtering by `junction_path` to route different volumes to different targets:
```json
{
  "source": ["fsx.ontap.audit"],
  "detail": { "junction_path": ["unix"] }
}
```

### XML Parsing Bug Fix
Never use `element or fallback` with ElementTree - always use `if element is None` due to Element truthiness behavior.

### Verify EventBridge Delivery
Create a temporary catch-all rule to send events to CloudWatch Logs. Requires:
1. A `/aws/events/fsx-audit-debug` log group
2. A `logs:put-resource-policy` allowing `events.amazonaws.com` to write to `/aws/events/*`
3. An EventBridge rule on `FsxAuditStack-file-events` bus matching `{"source":["fsx.ontap.audit"]}`
4. CloudWatch Logs target on that rule

See README.md "Verifying EventBridge Events" for full commands.

## Common Tasks

### Add New Event Type
1. Edit `parse_xml_audit()` in `lambda/audit_processor/index.py`
2. Add event ID to filter (currently only `4656` for file create)
3. Update event schema if adding new fields

### Route Events by Volume
1. Create EventBridge rule filtering by `junction_path`
2. Add target (Lambda, SQS, SNS, etc.)
3. No code changes needed

### Add New Event Consumer
1. Create new Lambda function
2. Create EventBridge rule to route events
3. Or subscribe to SQS queue

### Modify Infrastructure
1. Edit `infra/fsx_audit_stack.py`
2. Run `cdk diff` to preview
3. Run `cdk deploy` to apply

## Detailed Documentation

See `.agents/summary/` for comprehensive docs:
- `index.md` - Documentation index and quick reference
- `architecture.md` - System architecture diagrams
- `components.md` - Component details and functions
- `interfaces.md` - Event schema and API contracts
- `data_models.md` - Audit log format and parsing
- `workflows.md` - Process flows and deployment
- `dependencies.md` - Libraries and AWS services
