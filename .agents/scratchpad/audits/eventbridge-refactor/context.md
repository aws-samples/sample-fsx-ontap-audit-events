# Context: EventBridge Refactor

## Task Description
Refactor the FSx ONTAP Audit Event Processing CDK project to:
1. Use EventBridge as the **primary and only** output from the audit processor Lambda
2. Make the thumbnail/file_processor Lambda an **optional example deployment**
3. Remove direct SQS/SNS/CloudWatch publishing from Lambda - let EventBridge handle routing
4. Simplify the architecture for "productization"

## Requirements

### Functional Requirements
1. **Core Deployment** (always deployed):
   - Audit Processor Lambda → EventBridge Event Bus
   - DynamoDB checkpoint table
   - EventBridge scheduler (triggers Lambda every 1 min)
   - Lambda failure DLQ

2. **Optional Example** (deployed via flag):
   - File Processor Lambda (thumbnail generation)
   - SQS queue for file events
   - EventBridge rule routing to SQS
   - Pillow Lambda layer

3. **Event Routing**:
   - All events published to EventBridge with `junction_path` for filtering
   - Customers create their own EventBridge rules to route to destinations
   - No hardcoded SQS/SNS/CloudWatch in Lambda

### Non-Functional Requirements
- Backward compatible CDK parameters
- Clear separation between core and example
- Minimal Lambda code (only EventBridge publishing)

## Existing Documentation
- **README.md**: Project overview, architecture, deployment instructions
- **AGENTS.md**: AI assistant guide with coding patterns

## Project Structure
```
audits/
├── infra/
│   ├── app.py                 # CDK entry point
│   └── fsx_audit_stack.py     # Main stack (TO MODIFY)
├── lambda/
│   ├── audit_processor/       # Core Lambda (TO SIMPLIFY)
│   └── file_processor/        # Example Lambda (TO MAKE OPTIONAL)
├── layers/
│   ├── evtx/                  # Required for core
│   └── pillow/                # Only for example
└── tests/
```

## Implementation Paths

### Lambda Changes (`lambda/audit_processor/index.py`)
- Remove: `send_to_sqs_batch()`, `send_to_sns()`, `send_to_cloudwatch_logs()`
- Keep: `send_to_eventbridge()` (rename to `publish_events()`)
- Remove env vars: `QUEUE_URL`, `SNS_TOPIC_ARN`, `LOG_GROUP_NAME`
- Keep env vars: `EVENT_BUS_NAME`, `BUCKET`, `TABLE_NAME`, `AUDIT_PREFIX`

### Infrastructure Changes (`infra/fsx_audit_stack.py`)
- Add parameter: `deploy_example: bool = False`
- Core resources (always): DynamoDB, EventBridge bus, Audit Lambda, Scheduler, Lambda DLQ
- Example resources (conditional): SQS, File Processor Lambda, Pillow layer, EventBridge rule

### CDK App Changes (`infra/app.py`)
- Add context parameter: `deploy_example`

## Dependencies
- aws-cdk-lib (existing)
- boto3 (Lambda runtime)
- python-evtx (Lambda layer - core)
- Pillow (Lambda layer - example only)
