# Workflows

## Audit Log Processing Workflow

```mermaid
flowchart TD
    A[EventBridge Trigger] --> B[Get Checkpoint from DynamoDB]
    B --> C{First Run?}
    C -->|Yes| D[Initialize to Latest Log]
    C -->|No| E[List New Logs via S3]
    D --> E
    E --> F{New Logs Found?}
    F -->|No| G[Return: No work]
    F -->|Yes| H[Limit to MAX_LOGS_PER_INVOCATION]
    H --> I[For Each Log]
    I --> J[Download from S3]
    J --> K{XML or EVTX?}
    K -->|XML| L[Parse XML]
    K -->|EVTX| M[Parse EVTX]
    L --> N[Filter for File Creates]
    M --> N
    N --> O[Extract Event Fields]
    O --> P[Publish to Destinations]
    P --> Q[Update Checkpoint]
    Q --> R{More Logs?}
    R -->|Yes| I
    R -->|No| S[Return: Success]
    
    J -->|Error| T[Stop Processing]
    T --> S
```

## Event Publishing Workflow

```mermaid
flowchart LR
    A[Events List] --> B{EventBridge Enabled?}
    B -->|Yes| C[Put Events to Bus]
    B -->|No| D{SQS Enabled?}
    C --> D
    D -->|Yes| E[Send Message Batch]
    D -->|No| F{SNS Enabled?}
    E --> F
    F -->|Yes| G[Publish to Topic]
    F -->|No| H{CloudWatch Enabled?}
    G --> H
    H -->|Yes| I[Put Log Events]
    H -->|No| J[Done]
    I --> J
```

## Deployment Workflow

```mermaid
flowchart TD
    A[Clone Repository] --> B[Setup Python Environment]
    B --> C[Install Dependencies]
    C --> D[Build Lambda Layers]
    D --> E[Configure CDK Context]
    E --> F[CDK Bootstrap]
    F --> G[CDK Deploy]
    G --> H[Configure FSx ONTAP Auditing]
    H --> I[Verify Events Flow]
```

### Deployment Commands

```bash
# 1. Setup environment
cd audits
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt

# 2. Build layers (if needed)
cd scripts
./build_evtx_layer.sh
./build_pillow_layer.sh

# 3. Deploy infrastructure
cd ../infra
cdk bootstrap  # First time only
cdk deploy \
  -c audit_s3_access_point_alias=<alias> \
  -c audit_s3_access_point_name=<name> \
  -c file_s3_access_point_alias=<alias> \
  -c file_s3_access_point_name=<name>
```

## Testing Workflow

```mermaid
flowchart LR
    A[Unit Tests] --> B[Infrastructure Tests]
    B --> C[Integration Tests]
    
    subgraph "Unit Tests"
        A1[test_audit_processor.py]
        A2[test_file_processor.py]
    end
    
    subgraph "Infrastructure Tests"
        B1[test_infrastructure_stack.py]
        B2[test_iam_configuration.py]
    end
    
    subgraph "Integration Tests"
        C1[integration_test.py]
    end
```

### Test Commands

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_audit_processor.py -v

# Run with coverage
pytest tests/ --cov=lambda --cov-report=html
```

## Error Recovery Workflow

```mermaid
flowchart TD
    A[Lambda Invocation] --> B{Processing Error?}
    B -->|No| C[Update Checkpoint]
    B -->|Yes| D[Stop at Failed Log]
    D --> E[Log Error]
    E --> F[Send to Lambda DLQ]
    F --> G[Next Invocation Retries]
    G --> H[Resume from Last Checkpoint]
```

Key recovery behaviors:
1. **Per-log checkpointing**: Only successfully processed logs update checkpoint
2. **Stop on failure**: Prevents gaps in event delivery
3. **Lambda DLQ**: Captures failed invocations for analysis
4. **Automatic retry**: Next scheduled invocation resumes from checkpoint
