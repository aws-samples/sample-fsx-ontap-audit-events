# Research: Current Implementation

## Current Lambda Architecture

### publish_events() Function (index.py:429-447)
```python
def publish_events(event_list: List[Dict]):
    """Publish events to EventBridge for downstream routing."""
    if not event_list or not EVENT_BUS_NAME:
        return
    
    for i in range(0, len(event_list), 10):
        batch = event_list[i:i+10]
        entries = [
            {
                'Source': 'fsx.ontap.audit',
                'DetailType': 'File Event',
                'Detail': json.dumps(event),
                'EventBusName': EVENT_BUS_NAME
            }
            for event in batch
        ]
        events_client.put_events(Entries=entries)
```

### Event Structure
Each event contains:
- `svm_name` - SVM identifier
- `junction_path` - Volume junction path
- `file_path` - Full file path
- `filesystem_id` - FSx filesystem ID
- `operation`, `timestamp`, `user`, `user_ip`, etc.

### Current Environment Variables
- `BUCKET`, `AUDIT_PREFIX`, `TABLE_NAME`
- `EVENT_BUS_NAME` - Default EventBridge bus
- `MAX_KEYS`, `MAX_LOGS_PER_INVOCATION`

## Current CDK Stack

### Stack Parameters
- `audit_s3_access_point_name/alias`
- `file_s3_access_point_name/alias`
- `output_s3_access_point_name/alias`
- `deploy_example: bool = False`

### Core Resources Created
1. DynamoDB table (checkpoints)
2. EventBridge event bus
3. Audit Processor Lambda
4. EventBridge scheduler (1 min)
5. Lambda failure DLQ
6. EVTX layer

## Key Findings

1. **Event routing point**: `publish_events()` is the single point where routing logic should be added
2. **Event has routing keys**: Each event already contains `svm_name` and `junction_path`
3. **Batch processing**: Events are batched in groups of 10 - routing should maintain this
4. **CDK pattern**: Stack already supports conditional resource creation (`deploy_example`)

## Implementation Approach

### Lambda Changes
1. Add `ROUTING_CONFIG` env var (JSON string)
2. Parse config on module load
3. Build lookup dict: `{(svm_name, junction_path): destination_config}`
4. Modify `publish_events()` to:
   - Group events by destination
   - Route each group to appropriate destination
   - Send unmatched events to default EventBridge

### CDK Changes
1. Add `routing_config` parameter (file path)
2. Read and parse JSON file in CDK
3. Create resources for routes without `destination_arn`
4. Pass config JSON to Lambda env var
5. Grant IAM permissions for all destination types
