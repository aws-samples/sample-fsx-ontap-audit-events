# Documentation Index

> **For AI Assistants**: This index provides metadata about all documentation files. Use this as your primary reference to understand the codebase and locate detailed information.

## Quick Reference

| Question Type | Consult |
|--------------|---------|
| How does the system work? | [architecture.md](architecture.md) |
| What components exist? | [components.md](components.md) |
| What's the event format? | [interfaces.md](interfaces.md) |
| How are audit logs structured? | [data_models.md](data_models.md) |
| How do I deploy/test? | [workflows.md](workflows.md) |
| What libraries are used? | [dependencies.md](dependencies.md) |

## Documentation Files

### [codebase_info.md](codebase_info.md)
**Purpose**: Basic project metadata and structure overview.
**Contains**: Technology stack, repository structure, language support.
**Use when**: Getting initial orientation to the project.

### [architecture.md](architecture.md)
**Purpose**: System design and data flow documentation.
**Contains**: 
- High-level architecture diagram (Mermaid)
- Design patterns (event-driven, checkpoint, fan-out)
- Data flow sequence diagram
- Scalability considerations
**Use when**: Understanding how components interact, explaining system behavior.

### [components.md](components.md)
**Purpose**: Detailed component documentation.
**Contains**:
- Audit Processor Lambda (core) - all functions documented
- File Processor Lambda (example) - thumbnail generation
- CDK Infrastructure Stack - resource definitions
- Lambda Layers - EVTX and Pillow
- Build scripts and test suite
**Use when**: Modifying specific components, understanding function purposes.

### [interfaces.md](interfaces.md)
**Purpose**: API contracts and integration points.
**Contains**:
- File Event JSON schema (all fields documented)
- EventBridge event structure and example rules
- DynamoDB checkpoint schema
- S3 Access Point interface
- CDK stack parameters
**Use when**: Integrating with the system, creating EventBridge rules, understanding event format.

### [data_models.md](data_models.md)
**Purpose**: Data structure documentation.
**Contains**:
- XML audit log format with element paths
- EVTX format notes
- DynamoDB record structure
- ObjectName parsing logic (junction_path extraction)
- Computer field parsing (filesystem_id, svm_name)
**Use when**: Parsing audit logs, understanding field extraction logic.

### [workflows.md](workflows.md)
**Purpose**: Process and procedure documentation.
**Contains**:
- Audit log processing flowchart
- Event publishing flowchart
- Deployment workflow with commands
- Testing workflow
- Error recovery workflow
**Use when**: Deploying, testing, troubleshooting, understanding processing flow.

### [dependencies.md](dependencies.md)
**Purpose**: Dependency and version documentation.
**Contains**:
- Runtime dependencies (boto3, python-evtx, Pillow)
- Development dependencies (CDK, pytest)
- Lambda layer contents
- AWS service dependencies
- Version constraints
**Use when**: Adding dependencies, troubleshooting import errors, understanding requirements.

## Key Code Locations

| Component | Path |
|-----------|------|
| Audit Processor Lambda | `lambda/audit_processor/index.py` |
| File Processor Lambda | `lambda/file_processor/index.py` |
| CDK Stack | `infra/fsx_audit_stack.py` |
| CDK App Entry | `infra/app.py` |
| Unit Tests | `tests/test_*.py` |
| Integration Tests | `tests/integration_test.py` |

## Common Tasks

### Add a new event destination
1. See [interfaces.md](interfaces.md) for EventBridge rule examples
2. Create EventBridge rule filtering by `junction_path` or other fields
3. Route to Lambda, SQS, SNS, or other targets

### Modify event parsing
1. See [data_models.md](data_models.md) for audit log structure
2. Edit `parse_xml_audit()` or `parse_evtx_audit()` in audit processor
3. Update event schema in [interfaces.md](interfaces.md)

### Deploy to new environment
1. Follow deployment workflow in [workflows.md](workflows.md)
2. Configure CDK context parameters per [interfaces.md](interfaces.md)

### Debug processing issues
1. Check CloudWatch Logs for Lambda errors
2. Verify checkpoint in DynamoDB (see [data_models.md](data_models.md))
3. Review error recovery workflow in [workflows.md](workflows.md)
