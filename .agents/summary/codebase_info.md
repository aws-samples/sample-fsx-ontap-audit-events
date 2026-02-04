# Codebase Information

## Project Overview
- **Name**: FSx ONTAP Audit Event Processing
- **Type**: Event-driven serverless application
- **Primary Language**: Python 3.12
- **Infrastructure**: AWS CDK (Python)
- **Runtime**: AWS Lambda

## Technology Stack
| Category | Technology |
|----------|------------|
| Language | Python 3.12 |
| Infrastructure as Code | AWS CDK v2 |
| Compute | AWS Lambda |
| Queue | Amazon SQS |
| Database | Amazon DynamoDB |
| Scheduler | Amazon EventBridge |
| Storage | Amazon FSx for NetApp ONTAP |
| Image Processing | Pillow |
| Log Parsing | python-evtx, xml.etree |

## Dependencies
### Runtime
- boto3 (AWS SDK)
- Pillow (image processing)
- python-evtx (Windows Event Log parsing)

### Development
- pytest
- aws-cdk-lib
- constructs

## Repository Statistics
- **Lambda Functions**: 2
- **Lambda Layers**: 2
- **Test Files**: 5
- **Infrastructure Files**: 3
