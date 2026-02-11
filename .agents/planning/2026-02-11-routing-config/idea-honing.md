# Idea Honing: Routing Configuration

## Requirements Clarification

### Q1: Where should the routing config file be stored?

Options to consider:
- A) S3 bucket (Lambda reads on startup or periodically)
- B) DynamoDB table (same table as checkpoints, or separate)
- C) Lambda environment variable (JSON string)
- D) Bundled with Lambda code (requires redeploy to change)

**Answer:** C - Lambda environment variable (JSON string). Config passed via CDK context, stored as env var.

---

### Q2: What destination types should the routing config support?

Options to consider:
- A) SQS only
- B) SQS and SNS
- C) SQS, SNS, and CloudWatch Logs
- D) Any combination of SQS, SNS, CloudWatch Logs, and EventBridge (different bus)

**Answer:** D - Any combination. Each junction_path will have its own destination (SQS, SNS, CloudWatch Logs, or EventBridge).

---

### Q3: Should a route support multiple destinations for the same junction_path?

For example, could `/unix` route to BOTH an SQS queue AND CloudWatch Logs simultaneously?
- A) No, one destination per junction_path
- B) Yes, multiple destinations per junction_path (fan-out)

**Answer:** A - One destination per junction_path. If no destination is configured for a junction_path, default to EventBridge.

---

### Q4: Should routing also support filtering by svm_name in addition to junction_path?

Example config scenarios:
- A) Filter by junction_path only: `{"junction_path": "unix", "destination": {...}}`
- B) Filter by svm_name + junction_path: `{"svm_name": "svm1", "junction_path": "unix", "destination": {...}}`
- C) Support both - svm_name is optional, junction_path is required

**Answer:** B - Filter by both svm_name AND junction_path. Required because two SVMs can have the same junction_path, so both are needed to uniquely identify a route.

---

### Q5: What should the config format look like?

Example structure:
```json
{
  "routes": [
    {
      "svm_name": "svm1",
      "junction_path": "unix",
      "destination_type": "sqs",
      "destination_arn": "arn:aws:sqs:us-east-1:123456789:my-queue"
    },
    {
      "svm_name": "svm2",
      "junction_path": "ntfs_ap",
      "destination_type": "sns",
      "destination_arn": "arn:aws:sns:us-east-1:123456789:my-topic"
    }
  ]
}
```

Does this structure work, or would you prefer a different format?

**Answer:** Structure is good, but `destination_arn` should be optional. If not provided, CDK should create the resource (SQS queue, SNS topic, etc.) automatically.

Updated example:
```json
{
  "routes": [
    {
      "svm_name": "svm1",
      "junction_path": "unix",
      "destination_type": "sqs"
    },
    {
      "svm_name": "svm2",
      "junction_path": "ntfs_ap",
      "destination_type": "sns",
      "destination_arn": "arn:aws:sns:us-east-1:123456789:existing-topic"
    }
  ]
}
```

---

### Q6: How should CDK name auto-created resources?

When `destination_arn` is not provided and CDK creates the resource, what naming convention?

Options:
- A) `{stack_name}-{svm_name}-{junction_path}-{type}` (e.g., `FsxAuditStack-svm1-unix-queue`)
- B) `{svm_name}-{junction_path}-events` (e.g., `svm1-unix-events`)
- C) Let user provide an optional `name` field in the route config

**Answer:** A - `{stack_name}-{svm_name}-{junction_path}-{type}` naming convention.

---

### Q7: Should the Lambda need IAM permissions for all possible destination types, or only for configured ones?

Options:
- A) Grant permissions only for destination types actually configured (more secure, dynamic IAM)
- B) Grant permissions for all destination types upfront (simpler, but broader permissions)

**Answer:** B - Grant permissions for all destination types upfront (simpler implementation).

---

### Q8: For CloudWatch Logs destination, should each route create its own log group, or use a shared log group with different log streams?

Options:
- A) Separate log group per route (e.g., `/fsx/svm1-unix-events`)
- B) Shared log group with log streams per route (e.g., log group `/fsx/audit-events`, streams `svm1/unix`, `svm2/ntfs`)

**Answer:** A - Separate log group per route for isolation.

---

### Q9: Should wildcard matching be supported in routes?

For example:
- `"junction_path": "*"` matches all junction paths for an SVM
- `"svm_name": "*"` matches all SVMs

Options:
- A) No wildcards - exact match only
- B) Support `*` wildcard for catch-all routes

**Answer:** A - No wildcards, exact match only. Unmatched events go to default EventBridge.

---

### Q10: How should the routing config be passed to CDK?

Options:
- A) JSON file path via context: `cdk deploy -c routing_config=./routes.json`
- B) Inline JSON via context: `cdk deploy -c routing_config='{"routes":[...]}'`
- C) Support both file path and inline JSON

**Answer:** A - JSON file path via context. CDK reads the file and passes config to Lambda as env var.
