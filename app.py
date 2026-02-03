#!/usr/bin/env python3
import aws_cdk as cdk
from fsx_audit_stack import FsxAuditStack

app = cdk.App()

FsxAuditStack(
    app,
    "FsxAuditStack",
    # Uncomment to specify environment
    # env=cdk.Environment(account='123456789012', region='us-east-1'),
)

app.synth()
