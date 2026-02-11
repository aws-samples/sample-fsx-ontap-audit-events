# Implementation Plan: Routing Configuration

## Implementation Checklist

- [x] Step 1: Add routing config parsing to Lambda
- [x] Step 2: Implement destination send functions
- [x] Step 3: Modify publish_events with routing logic
- [x] Step 4: Update CDK to load and pass routing config
- [x] Step 5: Add dynamic resource creation in CDK
- [x] Step 6: Add IAM permissions for all destination types
- [ ] Step 7: Update tests and documentation

---

## Step 1: Add Routing Config Parsing to Lambda

**Objective:** Parse ROUTING_CONFIG environment variable and build route lookup dictionary.

**Implementation Guidance:**
- Add `ROUTING_CONFIG` env var reading
- Parse JSON on module load (outside handler for cold start efficiency)
- Build `_routes` dict with `(svm_name, junction_path)` tuple keys
- Handle invalid JSON gracefully with logging

**Test Requirements:**
- Test valid config parsing
- Test empty/missing config
- Test invalid JSON handling
- Test route lookup by key

**Integration:** Foundation for routing logic in Step 3.

**Demo:** Lambda loads with routing config, can look up routes by svm_name/junction_path.

---

## Step 2: Implement Destination Send Functions

**Objective:** Create functions to send events to SQS, SNS, CloudWatch Logs, and EventBridge.

**Implementation Guidance:**
- Add `sqs_client`, `sns_client`, `logs_client` boto3 clients
- Implement `_send_to_sqs(queue_url, events)` with batching (10 per call)
- Implement `_send_to_sns(topic_arn, events)` 
- Implement `_send_to_cloudwatch_logs(log_group, events)`
- Implement `_send_to_eventbridge(bus_name, events)` (refactor existing)
- Add `_send_to_destination(dest_type, dest_arn, events)` dispatcher

**Test Requirements:**
- Test each send function with mocked clients
- Test batching for SQS
- Test error handling for each destination type

**Integration:** Uses existing event structure, called by routing logic in Step 3.

**Demo:** Can send test events to each destination type individually.

---

## Step 3: Modify publish_events with Routing Logic

**Objective:** Update publish_events to route events based on config.

**Implementation Guidance:**
- Group events by destination using `_routes` lookup
- Collect unmatched events for default EventBridge
- Call appropriate send function for each destination group
- Maintain batching efficiency

**Test Requirements:**
- Test routing with matching routes
- Test fallback to default EventBridge
- Test mixed routed and unrouted events
- Test empty routes config (all to default)

**Integration:** Combines Steps 1 and 2, replaces current publish_events.

**Demo:** Events route to correct destinations based on svm_name/junction_path.

---

## Step 4: Update CDK to Load and Pass Routing Config

**Objective:** Add routing_config_path parameter and pass config to Lambda.

**Implementation Guidance:**
- Add `routing_config_path: str = None` parameter to stack
- Read JSON file if path provided
- Pass config as `ROUTING_CONFIG` env var (JSON string)
- Update app.py to read context parameter

**Test Requirements:**
- Test stack creation with and without routing config
- Test Lambda env var contains config JSON

**Integration:** Connects CDK deployment to Lambda routing feature.

**Demo:** `cdk deploy -c routing_config=./routes.json` passes config to Lambda.

---

## Step 5: Add Dynamic Resource Creation in CDK

**Objective:** Create SQS/SNS/CloudWatch resources for routes without destination_arn.

**Implementation Guidance:**
- Loop through routes, check for missing destination_arn
- Create appropriate resource based on destination_type
- Use naming convention: `{stack_name}-{svm_name}-{junction_path}-{type}`
- Update route config with created resource ARN/URL
- Add stack outputs for created resources

**Test Requirements:**
- Test resource creation for each destination type
- Test existing ARN passthrough (no creation)
- Test naming convention

**Integration:** Builds on Step 4, resources available before Lambda env var set.

**Demo:** Routes without ARN get auto-created resources visible in CloudFormation.

---

## Step 6: Add IAM Permissions for All Destination Types

**Objective:** Grant Lambda permissions to send to SQS, SNS, CloudWatch Logs.

**Implementation Guidance:**
- Add SQS SendMessage/SendMessageBatch permissions
- Add SNS Publish permissions
- Add CloudWatch Logs CreateLogStream/PutLogEvents permissions
- Use broad resource scope (`*`) as per requirements

**Test Requirements:**
- Test IAM policies are created
- Test Lambda can access all destination types

**Integration:** Enables Lambda to use destinations created in Step 5.

**Demo:** Lambda can successfully send to all destination types without permission errors.

---

## Step 7: Update Tests and Documentation

**Objective:** Ensure comprehensive test coverage and update documentation.

**Implementation Guidance:**
- Update test_audit_processor.py with routing tests
- Update test_infrastructure_stack.py with routing config tests
- Update README.md with routing configuration section
- Update AGENTS.md with routing feature details

**Test Requirements:**
- All existing tests still pass
- New routing tests cover all scenarios
- CDK synth succeeds with routing config

**Integration:** Final validation of complete feature.

**Demo:** All tests pass, documentation reflects new feature, example routes.json provided.
