# Plan: EventBridge Refactor

## Test Strategy

### Infrastructure Tests (`tests/test_infrastructure_stack.py`)

| Test | Description | Expected |
|------|-------------|----------|
| `test_core_resources_always_created` | DynamoDB, EventBridge bus, Audit Lambda, Scheduler created | Pass |
| `test_example_resources_not_created_by_default` | SQS, File Processor, Pillow layer NOT created when `deploy_example=False` | Pass |
| `test_example_resources_created_when_enabled` | SQS, File Processor, EventBridge rule created when `deploy_example=True` | Pass |
| `test_audit_lambda_only_has_eventbridge_env` | Lambda env has EVENT_BUS_NAME, no QUEUE_URL/SNS_TOPIC_ARN/LOG_GROUP_NAME | Pass |

### Lambda Tests (`tests/test_audit_processor.py`)

| Test | Description | Expected |
|------|-------------|----------|
| `test_publish_events_only_eventbridge` | `publish_events()` only calls EventBridge | Pass |
| `test_publish_events_empty_list` | Empty list returns without API calls | Pass |
| `test_eventbridge_batch_size` | Events batched in groups of 10 | Pass |

## Implementation Plan

### Phase 1: Simplify Lambda (audit_processor/index.py)

1. Remove unused imports: `sqs`, `sns`, `logs`
2. Remove unused env vars: `QUEUE_URL`, `SNS_TOPIC_ARN`, `LOG_GROUP_NAME`
3. Remove functions: `send_to_sqs_batch`, `send_to_sns`, `send_to_cloudwatch_logs`
4. Simplify `publish_events()` to only call EventBridge

### Phase 2: Refactor CDK Stack (fsx_audit_stack.py)

1. Add `deploy_example: bool = False` parameter
2. Move to core section (always deployed):
   - DynamoDB table
   - EventBridge event bus
   - Audit Processor Lambda (simplified env vars)
   - EventBridge scheduler
   - Lambda failure DLQ
   - EVTX layer
3. Move to example section (conditional on `deploy_example`):
   - SQS queue + DLQ
   - SNS topic (remove entirely - users create their own)
   - CloudWatch log group (remove entirely)
   - File Processor Lambda
   - Pillow layer
   - EventBridge rule routing to SQS
   - SQS trigger for File Processor
4. Update outputs (conditional)

### Phase 3: Update CDK App (app.py)

1. Add `deploy_example` context parameter
2. Pass to stack constructor

### Phase 4: Update Tests

1. Update infrastructure tests for conditional resources
2. Update Lambda tests for simplified publish_events

## Implementation Checklist

- [ ] Lambda: Remove SQS/SNS/CloudWatch code
- [ ] Lambda: Simplify publish_events to EventBridge only
- [ ] CDK: Add deploy_example parameter
- [ ] CDK: Separate core vs example resources
- [ ] CDK: Add EventBridge rule for example (routes to SQS)
- [ ] CDK: Update outputs
- [ ] App: Add deploy_example context
- [ ] Tests: Update infrastructure tests
- [ ] Tests: Update Lambda tests
- [ ] Validate: All tests pass
- [ ] Validate: CDK synth succeeds
- [ ] Commit: Conventional commit message
