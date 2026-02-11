# Project Summary: Routing Configuration

## Artifacts Created

```
.agents/planning/2026-02-11-routing-config/
├── rough-idea.md                    # Initial concept
├── idea-honing.md                   # 10 Q&A requirements clarification
├── research/
│   └── current-implementation.md    # Analysis of existing code
├── design/
│   └── detailed-design.md           # Complete technical design
├── implementation/
│   └── plan.md                      # 7-step implementation plan
└── summary.md                       # This document
```

## Design Overview

Optional routing configuration that allows events to be directed to specific destinations (SQS, SNS, CloudWatch Logs, EventBridge) based on `svm_name` + `junction_path` matching. Unmatched events fall back to default EventBridge.

### Key Decisions
- Config via JSON file, passed as Lambda env var
- Exact match routing (no wildcards)
- One destination per route
- CDK auto-creates resources when ARN not provided
- Broad IAM permissions for simplicity

## Implementation Plan (7 Steps)

1. Add routing config parsing to Lambda
2. Implement destination send functions
3. Modify publish_events with routing logic
4. Update CDK to load and pass routing config
5. Add dynamic resource creation in CDK
6. Add IAM permissions for all destination types
7. Update tests and documentation

## Next Steps

1. Review the detailed design: `.agents/planning/2026-02-11-routing-config/design/detailed-design.md`
2. Generate code tasks from implementation plan
3. Execute tasks using code-assist SOP

## Example Usage

```bash
# Create routes.json
cat > routes.json << 'EOF'
{
  "routes": [
    {"svm_name": "svm1", "junction_path": "unix", "destination_type": "sqs"},
    {"svm_name": "svm2", "junction_path": "ntfs", "destination_type": "sns", "destination_arn": "arn:aws:sns:..."}
  ]
}
EOF

# Deploy with routing
cdk deploy -c routing_config=./routes.json
```
