# Architecture

## System Overview

```mermaid
graph TB
    subgraph "FSx ONTAP"
        A[NFS/SMB Clients] --> B[Data Volume]
        B --> C[Audit Logs]
    end
    
    subgraph "AWS Serverless"
        D[EventBridge<br/>1 min schedule] --> E[Audit Processor<br/>Lambda]
        E --> F[DynamoDB<br/>Checkpoint]
        E --> G[SQS Queue]
        G --> H[File Processor<br/>Lambda]
        H --> I[Output Volume]
    end
    
    C -->|S3 Access Point| E
    B -->|S3 Access Point| H
    H -->|S3 Access Point| I
```

## Data Flow

```mermaid
sequenceDiagram
    participant Client as NFS/SMB Client
    participant FSx as FSx ONTAP
    participant EB as EventBridge
    participant AP as Audit Processor
    participant DDB as DynamoDB
    participant SQS as SQS Queue
    participant FP as File Processor
    
    Client->>FSx: Write file
    FSx->>FSx: Write audit log
    EB->>AP: Trigger (every 1 min)
    AP->>DDB: Get checkpoint
    AP->>FSx: List new audit logs
    AP->>FSx: Read audit log
    AP->>AP: Parse XML/EVTX
    AP->>SQS: Send file events
    AP->>DDB: Update checkpoint
    SQS->>FP: Trigger
    FP->>FSx: Read original file
    FP->>FP: Generate thumbnail
    FP->>FSx: Write thumbnail
```

## Design Patterns

### Checkpoint-based Processing
- Uses DynamoDB to track last processed audit log
- S3 `StartAfter` parameter for efficient listing
- Avoids reprocessing on Lambda restarts

### Active Log Detection
- Skips `*_last.xml` files (currently being written)
- Prevents reading incomplete audit data

### First-Run Initialization
- On first deployment, skips to latest log
- Avoids processing historical backlog

### Separate Input/Output Volumes
- Reads from audited volume
- Writes to separate output volume
- Prevents feedback loop from generated files
