"""
Tests for IAM roles and permissions.
"""
import sys
import os

# Add infra path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'infra'))

import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from fsx_audit_stack import FsxAuditStack

# Paths relative to tests directory
LAMBDA_PATH = os.path.join(os.path.dirname(__file__), '..', 'lambda')
LAYERS_PATH = os.path.join(os.path.dirname(__file__), '..', 'layers')


def create_stack(deploy_example=False):
    """Helper to create stack with correct paths."""
    app = cdk.App()
    return FsxAuditStack(
        app,
        "TestStack",
        audit_s3_access_point_alias="test-audit-alias",
        file_s3_access_point_alias="test-file-alias",
        lambda_path=LAMBDA_PATH,
        layers_path=LAYERS_PATH,
        deploy_example=deploy_example,
    )


class TestCoreIAMConfiguration:
    """Test IAM for core infrastructure."""

    def test_audit_processor_has_dynamodb_permissions(self):
        """Verify audit processor can read/write DynamoDB."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "dynamodb:BatchGetItem",
                                "dynamodb:GetItem",
                            ]),
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )

    def test_audit_processor_has_eventbridge_permissions(self):
        """Verify audit processor can put events to EventBridge."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": "events:PutEvents",
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )

    def test_audit_processor_has_s3_permissions(self):
        """Verify audit processor can read from S3 access point."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "s3:GetObject",
                                "s3:ListBucket"
                            ]),
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )

    def test_iam_roles_created(self):
        """Verify IAM roles are created for Lambda functions."""
        stack = create_stack()
        template = Template.from_stack(stack)

        # Should have at least 1 IAM role for audit processor
        roles = template.find_resources("AWS::IAM::Role")
        assert len(roles) >= 1

    def test_lambda_execution_role_trust_policy(self):
        """Verify Lambda execution role has correct trust policy."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Role",
            {
                "AssumeRolePolicyDocument": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "Service": "lambda.amazonaws.com"
                            }
                        }
                    ]
                }
            }
        )


class TestExampleIAMConfiguration:
    """Test IAM for example infrastructure."""

    def test_file_processor_has_s3_read_permissions(self):
        """Verify file processor can read from S3."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": "s3:GetObject",
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )

    def test_file_processor_has_s3_write_permissions(self):
        """Verify file processor can write to S3."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": "s3:PutObject",
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )

    def test_file_processor_has_sqs_permissions(self):
        """Verify file processor can consume from SQS."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                            ]),
                            "Effect": "Allow"
                        })
                    ])
                }
            }
        )
