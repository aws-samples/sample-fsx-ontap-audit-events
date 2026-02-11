# FSx ONTAP Audit Event Processing

Event-driven serverless file processing for FSx ONTAP using audit logs.

## Overview

This project implements an event-driven architecture for processing file operations on FSx ONTAP file systems accessed via NFS/SMB protocols. Since NFS/SMB writes don't trigger S3 Event Notifications, the solution uses ONTAP's native audit logging capability combined with serverless AWS components.

**Key Features:**

- ✅ Detects file creation events from ONTAP audit logs (XML/EVTX formats)
- ✅ Checkpoint-based processing for efficiency (99% reduction in S3 API calls)
- ✅ Automatic thumbnail generation for uploaded images
- ✅ Writes thumbnails to separate FSx ONTAP volume (avoids feedback loop)
- ✅ No data movement - files remain on FSx ONTAP
- ✅ ~2 minute latency from file creation to processing (with 1-min log rotation)

## Architecture

```
FSx ONTAP (NFS/SMB) → Audit Logs → EventBridge → Lambda (Audit Processor)
                                                      ↓
                                                  DynamoDB (Checkpoint)
                                                      ↓
                                                    SQS Queue
                                                      ↓
                                              Lambda (File Processor)
                                                      ↓
                                            FSx ONTAP (Output Volume)
```

### Components

- **DynamoDB**: Checkpoint tracking for processed audit logs
- **SQS**: Event queue with dead-letter queue (3 retries)
- **EventBridge**: Scheduled trigger (every 1 minute)
- **Lambda (Audit Processor)**: Parses audit logs, extracts file events
- **Lambda (File Processor)**: Generates thumbnails for images
- **S3 Access Points**: Unified access for reading audit logs and writing thumbnails

## Project Structure

```
audits/
├── infra/                    # CDK infrastructure (deploy from here)
│   ├── app.py               # CDK app entry point
│   ├── fsx_audit_stack.py   # Stack definition
│   └── cdk.json             # CDK configuration
├── lambda/                   # Lambda function code
│   ├── audit_processor/     # Parses audit logs → SQS
│   │   └── index.py
│   └── file_processor/      # Generates thumbnails
│       └── index.py
├── layers/                   # Lambda layers
│   ├── evtx/                # python-evtx layer
│   └── pillow/              # Pillow layer
├── scripts/                  # Build scripts
│   ├── build_evtx_layer.sh
│   ├── build_pillow_layer.sh
│   └── activate.sh
├── tests/                    # Unit & integration tests
├── .agents/summary/          # AI assistant documentation
└── AGENTS.md                 # AI assistant guide
```

## Quick Start

### Prerequisites

1. **FSx ONTAP File System** with:
   - Audit volume (for audit logs)
   - Data volume (for source files)
   - Output volume (for thumbnails - can be same as data volume if not audited)

2. **S3 Access Points** configured for each volume

3. **Python 3.12+** and **uv** package manager

4. **AWS CDK CLI**:

   ```bash
   npm install -g aws-cdk
   ```

### Setup

```bash
cd /path/to/audits

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt

# Build Lambda layers
./scripts/build_evtx_layer.sh
./scripts/build_pillow_layer.sh
```

### Deploy Infrastructure

```bash
cd infra
source ../.venv/bin/activate

cdk deploy \
  -c audit_s3_access_point_name=audit-ap \
  -c audit_s3_access_point_alias=audit-ap-xxxxx-s3alias \
  -c file_s3_access_point_name=data-ap \
  -c file_s3_access_point_alias=data-ap-xxxxx-s3alias \
  -c output_s3_access_point_name=output-ap \
  -c output_s3_access_point_alias=output-ap-xxxxx-s3alias
```

### Optional: Event Routing Configuration

Route audit events to different destinations based on SVM name and junction path:

```bash
# Create routing config file
cat > routes.json << 'EOF'
{
  "routes": [
    {"svm_name": "svm1", "junction_path": "unix", "destination_type": "sqs"},
    {"svm_name": "svm2", "junction_path": "ntfs", "destination_type": "sns", "destination_arn": "arn:aws:sns:us-east-1:123456789:my-topic"},
    {"svm_name": "svm3", "junction_path": "data", "destination_type": "cloudwatch_logs"}
  ]
}
EOF

# Deploy with routing
cdk deploy -c routing_config_path=./routes.json
```

**Routing Options:**
- `destination_type`: `sqs`, `sns`, `cloudwatch_logs`, or `eventbridge`
- `destination_arn`: Optional - CDK creates resource if not provided
- Events not matching any route go to the default EventBridge bus

## ONTAP Audit Configuration

SSH to FSx ONTAP management endpoint and configure auditing:

```bash
# Create audit configuration with 1-minute rotation
vserver audit create -vserver <svm-name> \
  -destination /audit \
  -format xml \
  -rotate-schedule-minute 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59 \
  -guarantee true

# Enable audit logging
vserver audit enable -vserver <svm-name>

# Verify configuration
vserver audit show -vserver <svm-name>
```

**Configuration Options:**

- **Format**: `xml` (recommended) or `evtx`
- **Rotation**: Every minute for lowest latency
- **Guarantee**: `true` for synchronous logging (no missed events)

## Environment Variables

### Audit Processor Lambda

| Variable | Description |
|----------|-------------|
| `BUCKET` | S3 Access Point alias for audit logs |
| `AUDIT_PREFIX` | Path prefix for audit logs (default: empty) |
| `TABLE_NAME` | DynamoDB table name for checkpoint |
| `EVENT_BUS_NAME` | EventBridge bus name for file events |
| `ROUTING_CONFIG` | JSON routing config (optional) |
| `MAX_KEYS` | Maximum logs to process per run (default: 100) |

### File Processor Lambda

| Variable | Description |
|----------|-------------|
| `S3_ACCESS_POINT_ALIAS` | S3 Access Point alias for reading files |
| `OUTPUT_S3_ACCESS_POINT_ALIAS` | S3 Access Point alias for writing thumbnails |

## Testing

### Unit Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

### Integration Test

```bash
python tests/integration_test.py \
  --audit-alias <audit-ap-alias> \
  --file-alias <file-ap-alias> \
  --region eu-west-1
```

## CDK Commands

Run from the `infra/` directory:

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

## Monitoring

### CloudWatch Logs

- **Audit Processor**: `/aws/lambda/FsxAuditStack-AuditLogProcessor-*`
- **File Processor**: `/aws/lambda/FsxAuditStack-FileProcessor-*`

### Debugging Commands

```bash
# View Lambda logs
aws logs tail /aws/lambda/FsxAuditStack-AuditLogProcessor-* --follow

# Check SQS queue depth
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessages

# Check DynamoDB checkpoint
aws dynamodb get-item \
  --table-name <table-name> \
  --key '{"pk": {"S": "tracker"}}'
```

## Troubleshooting

### No logs being processed

- Check ONTAP audit is enabled: `vserver audit show`
- Verify audit logs are being written to FSx volume
- Check Lambda has S3 permissions
- Verify DynamoDB checkpoint is not stuck

### Thumbnail not generated

- Check file is a supported image format (JPEG, PNG, GIF, WebP, TIFF, BMP)
- Verify file exists in FSx volume
- Check Lambda logs for errors

### SQS messages in DLQ

- Check Lambda logs for processing errors
- Verify S3 Access Point is accessible
- Check IAM permissions

### Feedback loop (thumbnails triggering new events)

- Use separate `output_s3_access_point_alias` pointing to a non-audited volume

## Key Design Decisions

1. **First-run initialization**: On first deployment, skips to latest audit log to avoid processing historical backlog

2. **Active log detection**: Skips `*_last.xml` files that are currently being written

3. **Separate output volume**: Writes thumbnails to different volume to prevent feedback loop

4. **Checkpoint-based processing**: Uses S3 `StartAfter` for efficient listing without re-scanning

## References

- [FSx ONTAP S3 Access Points](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/accessing-data-via-s3-access-points.html)
- [ONTAP Audit Configuration](https://docs.aws.amazon.com/fsx/latest/ONTAPGuide/file-access-auditing.html)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.
