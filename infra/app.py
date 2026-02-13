# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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

# Get S3 Access Point aliases from context
audit_alias = app.node.try_get_context("audit_s3_access_point_alias")
file_alias = app.node.try_get_context("file_s3_access_point_alias")
output_alias = app.node.try_get_context("output_s3_access_point_alias")

# Optional: deploy thumbnail generation example
deploy_example = app.node.try_get_context("deploy_example") or False

# Optional: routing config file path
routing_config_path = app.node.try_get_context("routing_config_path")

FsxAuditStack(
    app,
    "FsxAuditStack",
    audit_s3_access_point_alias=audit_alias,
    file_s3_access_point_alias=file_alias,
    output_s3_access_point_alias=output_alias,
    lambda_path=lambda_path,
    layers_path=layers_path,
    deploy_example=deploy_example,
    routing_config_path=routing_config_path,
    # Uncomment to specify environment
    # env=cdk.Environment(account='486768734100', region='eu-west-1'),
)

app.synth()
