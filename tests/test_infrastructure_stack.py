"""
Tests for CDK infrastructure stack.
"""
import aws_cdk as cdk
from aws_cdk.assertions import Template, Match
from fsx_audit_stack import FsxAuditStack


class TestInfrastructureStack:
    """Test that the CDK infrastructure stack is correctly defined."""

    def test_dynamodb_table_created(self):
        """Verify DynamoDB table with correct configuration."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "BillingMode": "PAY_PER_REQUEST",
                "PointInTimeRecoverySpecification": {
                    "PointInTimeRecoveryEnabled": True
                },
                "KeySchema": [
                    {
                        "AttributeName": "pk",
                        "KeyType": "HASH"
                    }
                ],
            }
        )

    def test_sqs_dlq_created(self):
        """Verify SQS dead letter queue with 14-day retention."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::SQS::Queue",
            {
                "MessageRetentionPeriod": 1209600  # 14 days in seconds
            }
        )

    def test_sqs_main_queue_created(self):
        """Verify SQS main queue with correct configuration."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::SQS::Queue",
            {
                "VisibilityTimeout": 300,
                "MessageRetentionPeriod": 345600,  # 4 days in seconds
                "RedrivePolicy": Match.object_like({
                    "maxReceiveCount": 3
                })
            }
        )

    def test_eventbridge_schedule_rule(self):
        """Verify EventBridge rule with 1-minute schedule."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "ScheduleExpression": "rate(1 minute)"
            }
        )

    def test_audit_processor_lambda(self):
        """Verify audit processor Lambda configuration."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.12",
                "Timeout": 60,
                "MemorySize": 256,
                "Environment": {
                    "Variables": Match.object_like({
                        "BUCKET": "test-audit-alias",
                        "AUDIT_PREFIX": "audit/",
                        "MAX_KEYS": "100"
                    })
                }
            }
        )

    def test_file_processor_lambda(self):
        """Verify file processor Lambda configuration."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.12",
                "Timeout": 300,
                "MemorySize": 1024,
                "Environment": {
                    "Variables": {
                        "S3_ACCESS_POINT_ALIAS": "test-file-alias"
                    }
                }
            }
        )

    def test_stack_outputs(self):
        """Verify stack outputs are defined."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Check that outputs exist
        outputs = template.find_outputs("*")
        output_keys = list(outputs.keys())
        
        assert any("StateTableName" in key for key in output_keys)
        assert any("QueueUrl" in key for key in output_keys)
        assert any("DLQArn" in key for key in output_keys)
        assert any("AuditS3AccessPointAlias" in key for key in output_keys)
        assert any("FileS3AccessPointAlias" in key for key in output_keys)

    def test_resource_count(self):
        """Verify expected number of resources are created."""
        app = cdk.App()
        stack = FsxAuditStack(
            app,
            "TestStack",
            audit_s3_access_point_alias="test-audit-alias",
            file_s3_access_point_alias="test-file-alias",
        )
        template = Template.from_stack(stack)

        # Should have 1 DynamoDB table
        template.resource_count_is("AWS::DynamoDB::Table", 1)
        
        # Should have 2 SQS queues (main + DLQ)
        template.resource_count_is("AWS::SQS::Queue", 2)
        
        # Should have 2 Lambda functions
        template.resource_count_is("AWS::Lambda::Function", 2)
        
        # Should have 1 EventBridge rule
        template.resource_count_is("AWS::Events::Rule", 1)
