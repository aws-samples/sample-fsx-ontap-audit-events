#!/usr/bin/env python3
"""
CDK app entry point for FSx ONTAP Audit Event Processing.

This app defines the infrastructure stack for processing audit logs
from FSx ONTAP file systems and publishing events to EventBridge.
"""
import aws_cdk as cdk
from fsx_audit_stack import FsxAuditStack

app = cdk.App()

# Get paths from context (for running from infra/ directory)
lambda_path = app.node.try_get_context("lambda_path") or "../lambda"
layers_path = app.node.try_get_context("layers_path") or "../layers"

# Get S3 Access Point names and aliases from context
audit_name = app.node.try_get_context("audit_s3_access_point_name")
audit_alias = app.node.try_get_context("audit_s3_access_point_alias")
file_name = app.node.try_get_context("file_s3_access_point_name")
file_alias = app.node.try_get_context("file_s3_access_point_alias")
output_name = app.node.try_get_context("output_s3_access_point_name")
output_alias = app.node.try_get_context("output_s3_access_point_alias")

# Optional: deploy thumbnail generation example
deploy_example = app.node.try_get_context("deploy_example") or False

# Optional: routing config file path
routing_config_path = app.node.try_get_context("routing_config_path")

FsxAuditStack(
    app,
    "FsxAuditStack",
    audit_s3_access_point_name=audit_name,
    audit_s3_access_point_alias=audit_alias,
    file_s3_access_point_name=file_name,
    file_s3_access_point_alias=file_alias,
    output_s3_access_point_name=output_name,
    output_s3_access_point_alias=output_alias,
    lambda_path=lambda_path,
    layers_path=layers_path,
    deploy_example=deploy_example,
    routing_config_path=routing_config_path,
    # Uncomment to specify environment
    # env=cdk.Environment(account='486768734100', region='eu-west-1'),
)

app.synth()
