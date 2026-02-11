# Codebase Information

## Project Overview
- **Name**: FSx ONTAP Audit Event Processing
- **Type**: AWS CDK Infrastructure + Lambda Functions
- **Language**: Python 3.12
- **Package Manager**: uv
- **Total Files**: 511 (including dependencies)
- **Core Files**: ~20 (excluding layers/dependencies)
- **Lines of Code**: ~40,000 (including bundled libraries)

## Technology Stack
- **Infrastructure**: AWS CDK (Python)
- **Runtime**: AWS Lambda (Python 3.12)
- **Storage**: Amazon DynamoDB, Amazon S3 (via Access Points)
- **Messaging**: Amazon SQS, Amazon SNS, Amazon EventBridge
- **Logging**: Amazon CloudWatch Logs
- **File System**: Amazon FSx for NetApp ONTAP

## Repository Structure
```
audits/
├── infra/                    # CDK infrastructure code
├── lambda/                   # Lambda function source
│   ├── audit_processor/      # Core audit log parser
│   └── file_processor/       # Example thumbnail generator
├── layers/                   # Lambda layers (bundled dependencies)
│   ├── evtx/                 # Windows Event Log parser
│   └── pillow/               # Image processing library
├── scripts/                  # Build and setup scripts
├── tests/                    # Unit and integration tests
└── .agents/summary/          # AI assistant documentation
```

## Supported Languages
- Python (primary)
- Shell scripts (build automation)

## Key Dependencies
- aws-cdk-lib
- boto3
- python-evtx (for EVTX parsing)
- Pillow (for image processing - example use case)
- pytest (development)
