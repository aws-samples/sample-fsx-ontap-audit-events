# Workflows

## Main Processing Flow

```mermaid
flowchart TD
    A[EventBridge Trigger] --> B[Get Checkpoint]
    B --> C{First Run?}
    C -->|Yes| D[Initialize to Latest Log]
    C -->|No| E[List New Logs]
    D --> E
    E --> F{New Logs?}
    F -->|No| G[Return]
    F -->|Yes| H[Process Each Log]
    H --> I[Parse XML/EVTX]
    I --> J[Filter File Events]
    J --> K[Send to SQS]
    K --> L[Update Checkpoint]
    L --> G
```

## Thumbnail Generation Flow

```mermaid
flowchart TD
    A[SQS Trigger] --> B[Parse Message]
    B --> C{Is Image?}
    C -->|No| D[Skip]
    C -->|Yes| E[Read from FSx]
    E --> F[Generate Thumbnail]
    F --> G[Write to Output Volume]
    G --> H[Return Success]
    D --> H
```

## Audit Log Lifecycle

```mermaid
flowchart LR
    A[Active Log<br/>*_last.xml] -->|Rotation| B[Completed Log<br/>*_D2026-..._0000.xml]
    B -->|Processing| C[Events in SQS]
    C -->|Consumption| D[Thumbnails Generated]
```

## Error Handling

```mermaid
flowchart TD
    A[Process File] --> B{Success?}
    B -->|Yes| C[Acknowledge Message]
    B -->|No| D[Throw Exception]
    D --> E[SQS Retry]
    E --> F{Retry Count < 3?}
    F -->|Yes| A
    F -->|No| G[Move to DLQ]
```

## Deployment Workflow

```bash
# 1. Build Lambda layers
./scripts/build_evtx_layer.sh
./scripts/build_pillow_layer.sh

# 2. Deploy infrastructure
cd infra
cdk deploy \
  -c audit_s3_access_point_alias=<audit-alias> \
  -c file_s3_access_point_alias=<file-alias> \
  -c output_s3_access_point_alias=<output-alias>
```
