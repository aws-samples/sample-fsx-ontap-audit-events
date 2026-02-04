# AGENTS.md - AI Assistant Guide

> This file provides context for AI coding assistants working on this codebase.

## Project Overview

**FSx ONTAP Audit Event Processing** - Event-driven serverless application that monitors FSx ONTAP audit logs and generates thumbnails for uploaded images.

## Directory Structure

```
audits/
├── infra/                    # CDK infrastructure (deploy from here)
│   ├── app.py               # CDK app entry point
│   ├── fsx_audit_stack.py   # Stack definition  
│   └── cdk.json             # CDK config with context params
├── lambda/                   # Lambda function code
│   ├── audit_processor/     # Parses audit logs, sends to SQS
│   │   └── index.py         # Main handler
│   └── file_processor/      # Generates thumbnails
│       └── index.py         # Main handler
├── layers/                   # Lambda layers (pre-built)
│   ├── evtx/                # python-evtx for EVTX parsing
│   └── pillow/              # Pillow for image processing
├── scripts/                  # Build scripts
│   ├── build_evtx_layer.sh
│   └── build_pillow_layer.sh
├── tests/                    # Unit & integration tests
└── .agents/summary/          # Detailed documentation
```

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Audit Processor | `lambda/audit_processor/index.py` | Parse ONTAP audit logs, extract file events |
| File Processor | `lambda/file_processor/index.py` | Generate thumbnails for images |
| CDK Stack | `infra/fsx_audit_stack.py` | AWS infrastructure definition |

## Coding Patterns

### Lambda Handler Pattern
```python
def lambda_handler(event, context):
    """Main entry point."""
    # 1. Parse input
    # 2. Process
    # 3. Return response dict
    return {'statusCode': 200, ...}
```

### XML Namespace Handling
```python
# Always use explicit None checks, not 'or' operator
element = parent.find('ns:Child', ns)
if element is None:
    element = parent.find('Child')
```

### Environment Variables
- Access via `os.environ.get('VAR', 'default')`
- All config is externalized to env vars

## Testing

### Run Tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Test Files
- `tests/test_audit_processor.py` - Audit parsing tests
- `tests/test_file_processor.py` - Thumbnail generation tests
- `tests/test_infrastructure_stack.py` - CDK stack tests
- `tests/integration_test.py` - End-to-end tests

## Deployment

```bash
cd infra
source ../.venv/bin/activate
cdk deploy \
  -c audit_s3_access_point_name=<name> \
  -c audit_s3_access_point_alias=<alias> \
  -c file_s3_access_point_name=<name> \
  -c file_s3_access_point_alias=<alias> \
  -c output_s3_access_point_name=<name> \
  -c output_s3_access_point_alias=<alias>
```

## Important Implementation Details

### First-Run Behavior
On first deployment, `initialize_checkpoint_to_latest()` skips to the latest audit log to avoid processing historical backlog.

### Active Log Detection
Files matching `*_last.xml` are skipped as they're actively being written by ONTAP.

### Feedback Loop Prevention
Use separate `output_s3_access_point_alias` to write thumbnails to a different volume than the one being audited.

### XML Parsing Bug Fix
Never use `element or fallback` pattern with ElementTree - always use explicit `if element is None` checks due to Element truthiness behavior.

## Common Tasks

### Add New Event Type
1. Update `parse_xml_audit()` in `lambda/audit_processor/index.py`
2. Add event ID filter (currently only `4656` for file create)
3. Update SQS message format if needed

### Add New File Processor
1. Update `process_file_event()` in `lambda/file_processor/index.py`
2. Add format to `SUPPORTED_FORMATS` set
3. Implement processing logic

### Modify Infrastructure
1. Edit `infra/fsx_audit_stack.py`
2. Run `cdk diff` to preview changes
3. Run `cdk deploy` to apply

## Detailed Documentation

See `.agents/summary/` for comprehensive documentation:
- `index.md` - Documentation index
- `architecture.md` - System architecture
- `components.md` - Component details
- `interfaces.md` - APIs and data formats
- `workflows.md` - Process flows
