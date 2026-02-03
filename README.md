# FSx ONTAP Audit Event Processing

Event-driven serverless file processing for FSx ONTAP using audit logs.

## Quick Start

### Prerequisites

1. **FSx ONTAP File System** with two volumes:
   - Audit volume (for audit logs)
   - Data volume (for files and thumbnails)

2. **S3 Access Points** configured for both volumes:
   - Get the S3 Access Point **alias** (not ARN) for each volume
   - Example: `my-audit-ap-abc123-s3alias`

3. **Python 3.12+** and **uv** package manager

### Setup

```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies (already done if you followed setup)
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt
```

### Testing the Workflow

Run the integration test to verify end-to-end functionality:

```bash
python integration_test.py \
  --audit-alias your-audit-ap-abc123-s3alias \
  --file-alias your-data-ap-xyz789-s3alias \
  --region us-east-1
```

This test will:
1. ✓ Create a test image (800x600 blue JPEG)
2. ✓ Upload it to FSx via S3 Access Point
3. ✓ Generate a simulated audit log
4. ✓ Parse the audit log to extract file events
5. ✓ Generate a 200x200 thumbnail
6. ✓ Verify the thumbnail was created successfully

### Deploy Infrastructure

```bash
# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy stack
cdk deploy \
  -c audit_s3_access_point_alias=your-audit-ap-alias \
  -c file_s3_access_point_alias=your-data-ap-alias
```

Or update `app.py` with your aliases:

```python
FsxAuditStack(
    app,
    "FsxAuditStack",
    audit_s3_access_point_alias="your-audit-ap-abc123-s3alias",
    file_s3_access_point_alias="your-data-ap-xyz789-s3alias",
    env=cdk.Environment(account='123456789012', region='us-east-1'),
)
```

Then deploy:
```bash
cdk deploy
```

## Architecture

```
FSx ONTAP (NFS/SMB) → Audit Logs → EventBridge → Lambda (Processor)
                                                      ↓
                                                    SQS Queue
                                                      ↓
                                              Lambda (Thumbnail)
                                                      ↓
                                            FSx ONTAP (Thumbnails)
```

### Components

- **DynamoDB**: Checkpoint tracking for processed audit logs
- **SQS**: Event queue with dead-letter queue (3 retries)
- **EventBridge**: Scheduled trigger (every 1 minute)
- **Lambda (Audit Processor)**: Parses audit logs, extracts file events
- **Lambda (File Processor)**: Generates thumbnails for images

## Project Structure

```
.
├── app.py                          # CDK app entry point
├── fsx_audit_stack.py              # Infrastructure stack definition
├── lambda/
│   ├── audit_processor/            # Audit log processor Lambda
│   │   ├── index.py
│   │   └── requirements.txt
│   └── file_processor/             # Thumbnail generator Lambda
│       ├── index.py
│       └── requirements.txt
├── layers/
│   ├── evtx/                       # python-evtx layer
│   └── pillow/                     # Pillow layer
├── tests/                          # Unit tests
└── integration_test.py             # End-to-end test script
```

## Testing

```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_infrastructure_stack.py -v

# Run integration test
python integration_test.py --audit-alias <alias> --file-alias <alias>
```

## Configuration

### ONTAP Audit Configuration

```bash
# SSH to FSx ONTAP management endpoint
ssh fsxadmin@management.fs-xxxxx.fsx.us-east-1.amazonaws.com

# Create audit configuration
vserver audit create -vserver <svm-name> \
  -destination /audit \
  -format xml \
  -rotate-size 10MB \
  -rotate-schedule-minute */5 \
  -guarantee true

# Enable audit logging
vserver audit enable -vserver <svm-name>

# Verify configuration
vserver audit show -vserver <svm-name>
```

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### CDK Commands

```bash
# Synthesize CloudFormation template
cdk synth

# Show differences
cdk diff

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```

## Status

**Step 01: Infrastructure Setup** ✅ Complete
- [x] Task 1: Initialize CDK project
- [x] Task 2: Define infrastructure stack
- [x] Task 3: Configure IAM roles and dependencies

**Step 02-15: Implementation** 🚧 Pending
- [ ] Implement audit log processing logic
- [ ] Implement thumbnail generation logic
- [ ] Add integration tests
- [ ] Set up monitoring and alarms

## License

This project is for demonstration purposes.
