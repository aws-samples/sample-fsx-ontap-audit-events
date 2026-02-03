from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda as lambda_,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct


class FsxAuditStack(Stack):
    """
    CDK Stack for FSx ONTAP Audit Event Processing.
    
    This stack contains:
    - DynamoDB table for checkpoint tracking
    - SQS queues for event buffering
    - Lambda functions for audit processing and file processing
    - EventBridge schedule for triggering audit processor
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        audit_s3_access_point_alias: str = None,
        file_s3_access_point_alias: str = None,
        audit_prefix: str = "audit/",
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB state table for checkpoint tracking
        state_table = dynamodb.Table(
            self,
            "AuditLogStateTable",
            partition_key=dynamodb.Attribute(
                name="pk",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # SQS Dead Letter Queue
        dlq = sqs.Queue(
            self,
            "FileEventsDLQ",
            retention_period=Duration.days(14),
        )

        # SQS Main Queue
        queue = sqs.Queue(
            self,
            "FileEventsQueue",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(4),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            ),
        )

        # Placeholder Lambda functions (will be implemented in later tasks)
        # Audit Log Processor Lambda
        audit_processor = lambda_.Function(
            self,
            "AuditLogProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("lambda/audit_processor"),
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "BUCKET": audit_s3_access_point_alias or "",
                "AUDIT_PREFIX": audit_prefix,
                "TABLE_NAME": state_table.table_name,
                "QUEUE_URL": queue.queue_url,
                "MAX_KEYS": "100",
            },
        )

        # File Processor Lambda
        file_processor = lambda_.Function(
            self,
            "FileProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset("lambda/file_processor"),
            timeout=Duration.seconds(300),
            memory_size=1024,
            environment={
                "S3_ACCESS_POINT_ALIAS": file_s3_access_point_alias or "",
            },
        )

        # EventBridge schedule rule (every 1 minute)
        schedule_rule = events.Rule(
            self,
            "AuditProcessorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
        )
        
        schedule_rule.add_target(targets.LambdaFunction(audit_processor))

        # Stack outputs
        CfnOutput(
            self,
            "StateTableName",
            value=state_table.table_name,
            description="DynamoDB state table name",
        )

        CfnOutput(
            self,
            "QueueUrl",
            value=queue.queue_url,
            description="SQS queue URL for file events",
        )

        CfnOutput(
            self,
            "DLQArn",
            value=dlq.queue_arn,
            description="Dead letter queue ARN",
        )

        CfnOutput(
            self,
            "AuditS3AccessPointAlias",
            value=audit_s3_access_point_alias or "NOT_SET",
            description="S3 Access Point alias for audit logs",
        )

        CfnOutput(
            self,
            "FileS3AccessPointAlias",
            value=file_s3_access_point_alias or "NOT_SET",
            description="S3 Access Point alias for file data",
        )

        # Store references for IAM configuration in task 3
        self.state_table = state_table
        self.queue = queue
        self.audit_processor = audit_processor
        self.file_processor = file_processor
