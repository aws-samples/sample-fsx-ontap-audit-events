"""
Tests for IAM roles and permissions.
"""
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from fsx_audit_stack import FsxAuditStack


class TestIAMConfiguration:
    """Test that IAM roles and permissions are correctly configured."""

    def test_audit_processor_has_dynamodb_permissions(self):
        """Verify audit processor can read/write DynamoDB."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check for DynamoDB permissions in IAM policy
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                Match.string_like_regexp("dynamodb:.*"),
                            ]),
                            "Effect": "Allow",
                        })
                    ])
                }
            }
        )

    def test_audit_processor_has_sqs_permissions(self):
        """Verify audit processor can send messages to SQS."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check for SQS send permissions
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "sqs:SendMessage",
                                "sqs:GetQueueAttributes",
                                "sqs:GetQueueUrl",
                            ]),
                            "Effect": "Allow",
                        })
                    ])
                }
            }
        )

    def test_audit_processor_has_s3_permissions(self):
        """Verify audit processor can read from S3."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check for S3 read permissions
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": ["s3:GetObject", "s3:ListBucket"],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test-audit-alias",
                                "arn:aws:s3:::test-audit-alias/*",
                            ]
                        })
                    ])
                }
            }
        )

    def test_file_processor_has_s3_permissions(self):
        """Verify file processor can read/write to S3."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check for S3 read/write permissions
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": ["s3:GetObject", "s3:PutObject"],
                            "Effect": "Allow",
                        })
                    ])
                }
            }
        )

    def test_file_processor_has_sqs_permissions(self):
        """Verify file processor can consume messages from SQS."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check for SQS consume permissions
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with([
                        Match.object_like({
                            "Action": Match.array_with([
                                "sqs:ReceiveMessage",
                                "sqs:ChangeMessageVisibility",
                                "sqs:GetQueueUrl",
                                "sqs:DeleteMessage",
                                "sqs:GetQueueAttributes",
                            ]),
                            "Effect": "Allow",
                        })
                    ])
                }
            }
        )

    def test_iam_roles_created(self):
        """Verify IAM roles are created for Lambda functions."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Should have 2 IAM roles (one per Lambda)
        template.resource_count_is("AWS::IAM::Role", 2)

    def test_lambda_execution_role_trust_policy(self):
        """Verify Lambda execution roles have correct trust policy."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check trust policy allows Lambda service
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
