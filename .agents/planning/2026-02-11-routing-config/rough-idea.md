# Rough Idea: Optional Routing Configuration

## Initial Concept

Now that the default publishing destination is EventBridge, implement an optional routing function where:

1. User provides a config file with:
   - `svm-name`
   - `junction-path`
   - `destination`

2. This config overrides the default EventBridge publishing

3. Events matching the config criteria are routed to the specified destination instead of EventBridge

## Context

- Current architecture publishes ALL events to EventBridge
- EventBridge then routes based on rules
- This feature would allow pre-EventBridge routing at the Lambda level
- Use case: Direct routing to specific SQS/SNS without EventBridge hop
