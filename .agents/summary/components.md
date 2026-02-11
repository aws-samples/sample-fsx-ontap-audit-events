# Components

## Core Components

### 1. Audit Processor Lambda
**Location**: `lambda/audit_processor/index.py`

**Purpose**: Parses FSx ONTAP audit logs and publishes file events to configured destinations.

**Key Functions**:
| Function | Description |
|----------|-------------|
| `lambda_handler` | Entry point, orchestrates processing flow |
| `get_checkpoint` | Retrieves last processed log from DynamoDB |
| `update_checkpoint` | Saves processing state after each log |
| `list_new_logs` | Lists audit logs newer than checkpoint |
| `process_audit_log` | Downloads and parses a single log file |
| `parse_xml_audit` | Parses XML format audit logs |
| `parse_evtx_audit` | Parses Windows EVTX format logs |
| `publish_events` | Sends events to all configured destinations |
| `parse_object_name` | Extracts junction_path and file_path |
| `parse_computer` | Extracts filesystem_id and svm_name |
| `generate_event_id` | Creates deterministic dedup ID |

**Environment Variables**:
- `BUCKET`: S3 Access Point alias for audit logs
- `AUDIT_PREFIX`: Path prefix within bucket
- `TABLE_NAME`: DynamoDB table for checkpoints
- `EVENT_BUS_NAME`: EventBridge bus name
- `QUEUE_URL`: SQS queue URL (optional)
- `SNS_TOPIC_ARN`: SNS topic ARN (optional)
- `LOG_GROUP_NAME`: CloudWatch log group (optional)
- `MAX_LOGS_PER_INVOCATION`: Batch size limit (default: 10)

### 2. File Processor Lambda (Example)
**Location**: `lambda/file_processor/index.py`

**Purpose**: Example consumer that generates thumbnails for image files.

**Key Functions**:
| Function | Description |
|----------|-------------|
| `lambda_handler` | Processes SQS batch of file events |
| `process_file_event` | Handles single file event |
| `generate_thumbnail` | Creates thumbnail using Pillow |
| `extract_metadata` | Extracts image metadata |

**Note**: This is an optional example deployment demonstrating how to consume events.

### 3. CDK Infrastructure Stack
**Location**: `infra/fsx_audit_stack.py`

**Purpose**: Defines all AWS resources using CDK.

**Resources Created**:
- DynamoDB table (checkpoint storage)
- SQS queues (main + DLQ)
- SNS topic
- EventBridge event bus
- CloudWatch log group
- Lambda functions with layers
- EventBridge schedule rule
- IAM roles and policies

## Lambda Layers

### EVTX Layer
**Location**: `layers/evtx/`
- Contains `python-evtx` library for parsing Windows Event Log format
- Required for EVTX audit log support

### Pillow Layer
**Location**: `layers/pillow/`
- Contains Pillow image processing library
- Only needed for file_processor example

## Supporting Components

### Build Scripts
**Location**: `scripts/`
- `build_evtx_layer.sh`: Builds EVTX Lambda layer
- `build_pillow_layer.sh`: Builds Pillow Lambda layer
- `activate.sh`: Activates Python virtual environment

### Test Suite
**Location**: `tests/`
- `test_audit_processor.py`: Unit tests for audit parsing
- `test_file_processor.py`: Unit tests for thumbnail generation
- `test_infrastructure_stack.py`: CDK snapshot tests
- `test_iam_configuration.py`: IAM policy tests
- `integration_test.py`: End-to-end integration tests
