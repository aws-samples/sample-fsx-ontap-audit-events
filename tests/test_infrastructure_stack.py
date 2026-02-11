"""
Tests for CDK infrastructure stack.
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


class TestCoreInfrastructure:
    """Test core infrastructure (always deployed)."""

    def test_dynamodb_table_created(self):
        """Verify DynamoDB table with correct configuration."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "BillingMode": "PAY_PER_REQUEST",
                "KeySchema": [{"AttributeName": "pk", "KeyType": "HASH"}],
            }
        )

    def test_eventbridge_bus_created(self):
        """Verify EventBridge event bus is created."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Events::EventBus",
            {"Name": "TestStack-file-events"}
        )

    def test_lambda_dlq_created(self):
        """Verify Lambda failure DLQ with 14-day retention."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::SQS::Queue",
            {"MessageRetentionPeriod": 1209600}  # 14 days
        )

    def test_eventbridge_schedule_rule(self):
        """Verify EventBridge rule with 1-minute schedule."""
        stack = create_stack()
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Events::Rule",
            {"ScheduleExpression": "rate(1 minute)"}
        )

    def test_audit_processor_lambda(self):
        """Verify audit processor Lambda configuration."""
        stack = create_stack()
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
                        "MAX_KEYS": "100",
                    })
                }
            }
        )

    def test_audit_processor_no_sqs_env(self):
        """Verify audit processor does NOT have SQS/SNS/CloudWatch env vars."""
        stack = create_stack()
        template = Template.from_stack(stack)

        # Get all Lambda functions
        lambdas = template.find_resources("AWS::Lambda::Function")
        
        for logical_id, resource in lambdas.items():
            env_vars = resource.get("Properties", {}).get("Environment", {}).get("Variables", {})
            # Core audit processor should not have these
            if "AuditLogProcessor" in logical_id:
                assert "QUEUE_URL" not in env_vars
                assert "SNS_TOPIC_ARN" not in env_vars
                assert "LOG_GROUP_NAME" not in env_vars

    def test_core_resource_count(self):
        """Verify core deployment has minimal resources."""
        stack = create_stack(deploy_example=False)
        template = Template.from_stack(stack)

        template.resource_count_is("AWS::DynamoDB::Table", 1)
        template.resource_count_is("AWS::Lambda::Function", 1)  # Only audit processor
        template.resource_count_is("AWS::SQS::Queue", 1)  # Only Lambda DLQ
        template.resource_count_is("AWS::Events::EventBus", 1)

    def test_core_outputs(self):
        """Verify core stack outputs."""
        stack = create_stack(deploy_example=False)
        template = Template.from_stack(stack)

        outputs = template.find_outputs("*")
        output_keys = list(outputs.keys())
        
        assert any("StateTableName" in key for key in output_keys)
        assert any("EventBusName" in key for key in output_keys)
        assert any("LambdaDLQArn" in key for key in output_keys)


class TestExampleInfrastructure:
    """Test example infrastructure (optional deployment)."""

    def test_example_resources_created(self):
        """Verify example resources are created when enabled."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        # Should have 2 Lambda functions (audit + file processor)
        template.resource_count_is("AWS::Lambda::Function", 2)
        
        # Should have 3 SQS queues (Lambda DLQ + file events queue + file events DLQ)
        template.resource_count_is("AWS::SQS::Queue", 3)

    def test_file_processor_lambda(self):
        """Verify file processor Lambda configuration."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Runtime": "python3.12",
                "Timeout": 300,
                "MemorySize": 1024,
                "Environment": {
                    "Variables": Match.object_like({
                        "S3_ACCESS_POINT_ALIAS": "test-file-alias"
                    })
                }
            }
        )

    def test_eventbridge_rule_to_sqs(self):
        """Verify EventBridge rule routes to SQS."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        # Should have rule with SQS target
        template.has_resource_properties(
            "AWS::Events::Rule",
            {
                "EventPattern": {
                    "source": ["fsx.ontap.audit"],
                    "detail-type": ["File Event"]
                }
            }
        )

    def test_example_outputs(self):
        """Verify example stack outputs."""
        stack = create_stack(deploy_example=True)
        template = Template.from_stack(stack)

        outputs = template.find_outputs("*")
        output_keys = list(outputs.keys())
        
        assert any("QueueUrl" in key for key in output_keys)
        assert any("DLQArn" in key for key in output_keys)
