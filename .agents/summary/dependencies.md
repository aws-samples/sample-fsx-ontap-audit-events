# Dependencies

## Runtime Dependencies

### Core (audit_processor)
| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | (Lambda runtime) | AWS SDK for S3, DynamoDB, SQS, SNS, EventBridge, CloudWatch |
| python-evtx | bundled in layer | Parse Windows Event Log (EVTX) format |

### Example (file_processor)
| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | (Lambda runtime) | AWS SDK for S3 |
| Pillow | bundled in layer | Image processing and thumbnail generation |

## Development Dependencies

| Package | Purpose |
|---------|---------|
| aws-cdk-lib | Infrastructure as Code |
| constructs | CDK constructs library |
| pytest | Test framework |
| pytest-cov | Coverage reporting |
| moto | AWS service mocking |

## Lambda Layers

### EVTX Layer (`layers/evtx/`)
- **Contents**: python-evtx library and dependencies
- **Size**: ~2 MB
- **Build**: `scripts/build_evtx_layer.sh`

### Pillow Layer (`layers/pillow/`)
- **Contents**: Pillow library with native bindings
- **Size**: ~50 MB
- **Build**: `scripts/build_pillow_layer.sh`
- **Note**: Only needed for file_processor example

## AWS Service Dependencies

| Service | Purpose | Required |
|---------|---------|----------|
| Amazon S3 | Access audit logs via Access Points | Yes |
| Amazon DynamoDB | Checkpoint storage | Yes |
| Amazon EventBridge | Event routing | Yes (primary) |
| Amazon SQS | Event queuing | Optional |
| Amazon SNS | Event fan-out | Optional |
| Amazon CloudWatch Logs | Event persistence | Optional |
| AWS Lambda | Compute | Yes |
| AWS IAM | Permissions | Yes |

## External Dependencies

| Dependency | Purpose |
|------------|---------|
| FSx for NetApp ONTAP | Source file system with audit logging |
| S3 Access Points | Unified S3 interface to FSx volumes |
| ONTAP Audit Configuration | Must be enabled on SVM |

## Version Constraints

- **Python**: 3.12+ (Lambda runtime)
- **CDK**: 2.x
- **Node.js**: 18+ (for CDK CLI)
