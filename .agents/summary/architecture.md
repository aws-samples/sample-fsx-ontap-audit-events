# System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph "FSx ONTAP"
        NFS[NFS/SMB Clients]
        AV[Audit Volume]
        DV[Data Volumes]
    end
    
    subgraph "AWS Services"
        S3AP[S3 Access Points]
        EB[EventBridge Scheduler]
        AP[Audit Processor Lambda]
        DDB[(DynamoDB)]
        BUS[EventBridge Bus]
        SQS[SQS Queue]
        SNS[SNS Topic]
        CW[CloudWatch Logs]
        FP[File Processor Lambda]
    end
    
    NFS -->|writes| DV
    DV -->|audit events| AV
    AV -->|S3 protocol| S3AP
    EB -->|triggers every 1 min| AP
    S3AP -->|read logs| AP
    AP -->|checkpoint| DDB
    AP -->|publish events| BUS
    AP -->|optional| SQS
    AP -->|optional| SNS
    AP -->|optional| CW
    BUS -->|route by junction_path| SQS
    SQS -->|triggers| FP
    FP -->|read/write files| S3AP
```

## Design Patterns

### Event-Driven Architecture
The system uses polling-based event detection since NFS/SMB writes don't trigger native S3 events. ONTAP audit logs serve as the event source.

### Checkpoint Pattern
DynamoDB stores processing state to ensure:
- At-least-once delivery
- Efficient resumption after failures
- No reprocessing of old logs

### Fan-Out Pattern
EventBridge enables routing events to multiple destinations based on:
- Junction path (volume identifier)
- SVM name
- File type or path patterns

## Data Flow

```mermaid
sequenceDiagram
    participant Client as NFS/SMB Client
    participant FSx as FSx ONTAP
    participant S3 as S3 Access Point
    participant Lambda as Audit Processor
    participant DDB as DynamoDB
    participant EB as EventBridge
    participant Consumer as Event Consumers

    Client->>FSx: Write file
    FSx->>FSx: Generate audit log
    Note over Lambda: Triggered every 1 minute
    Lambda->>DDB: Get checkpoint
    Lambda->>S3: List new audit logs
    Lambda->>S3: Download & parse logs
    Lambda->>EB: Publish file events
    Lambda->>DDB: Update checkpoint
    EB->>Consumer: Route by junction_path
```

## Scalability Considerations

1. **Log Processing**: Limited to 10 logs per invocation to prevent timeouts
2. **Event Batching**: SQS/EventBridge batch up to 10 events per API call
3. **Checkpoint Granularity**: Per-log checkpointing for failure recovery
4. **Multi-Volume Support**: Events include junction_path for routing
