# Dependencies

## Runtime Dependencies

### Audit Processor Lambda
| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | (bundled) | AWS SDK |
| python-evtx | 0.8.1 | EVTX log parsing |

### File Processor Lambda
| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | (bundled) | AWS SDK |
| Pillow | 12.1.0 | Image processing |

---

## Development Dependencies

| Package | Purpose |
|---------|---------|
| pytest | Unit testing |
| aws-cdk-lib | Infrastructure as Code |
| constructs | CDK constructs |

---

## AWS Services

| Service | Purpose |
|---------|---------|
| Lambda | Serverless compute |
| DynamoDB | Checkpoint storage |
| SQS | Event queue |
| EventBridge | Scheduled triggers |
| S3 Access Points | FSx ONTAP access |
| CloudWatch Logs | Logging |
| IAM | Permissions |

---

## External Systems

| System | Integration |
|--------|-------------|
| FSx for NetApp ONTAP | File storage, audit logs |
| ONTAP Audit Subsystem | Generates audit events |

---

## Lambda Layer Contents

### EVTX Layer (`layers/evtx/python/`)
```
Evtx/           # python-evtx package
hexdump.py      # Dependency
```

### Pillow Layer (`layers/pillow/python/`)
```
PIL/            # Pillow package
pillow.libs/    # Native libraries
```
