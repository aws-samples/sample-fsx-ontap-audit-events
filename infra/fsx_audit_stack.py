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
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
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
        audit_s3_access_point_name: str = None,
        audit_s3_access_point_alias: str = None,
        file_s3_access_point_name: str = None,
        file_s3_access_point_alias: str = None,
        output_s3_access_point_name: str = None,
        output_s3_access_point_alias: str = None,
        lambda_path: str = "../lambda",
        layers_path: str = "../layers",
        audit_prefix: str = "",
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

        # Lambda layers for dependencies
        evtx_layer = lambda_.LayerVersion(
            self,
            "EvtxLayer",
            code=lambda_.Code.from_asset(f"{layers_path}/evtx"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="python-evtx library for EVTX parsing",
        )
        
        pillow_layer = lambda_.LayerVersion(
            self,
            "PillowLayer",
            code=lambda_.Code.from_asset(f"{layers_path}/pillow"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Pillow library for image processing",
        )

        # Placeholder Lambda functions (will be implemented in later tasks)
        # Audit Log Processor Lambda
        audit_processor = lambda_.Function(
            self,
            "AuditLogProcessor",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(f"{lambda_path}/audit_processor"),
            timeout=Duration.seconds(60),
            memory_size=256,
            layers=[evtx_layer],
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
            code=lambda_.Code.from_asset(f"{lambda_path}/file_processor"),
            timeout=Duration.seconds(300),
            memory_size=1024,
            layers=[pillow_layer],
            environment={
                "S3_ACCESS_POINT_ALIAS": file_s3_access_point_alias or "",
                "OUTPUT_S3_ACCESS_POINT_ALIAS": output_s3_access_point_alias or file_s3_access_point_alias or "",
            },
        )

        # EventBridge schedule rule (every 1 minute)
        schedule_rule = events.Rule(
            self,
            "AuditProcessorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
        )
        
        schedule_rule.add_target(targets.LambdaFunction(audit_processor))

        # Grant IAM permissions to audit processor Lambda
        state_table.grant_read_write_data(audit_processor)
        queue.grant_send_messages(audit_processor)
        
        # Grant S3 permissions for audit log access
        # Note: For FSx ONTAP S3 Access Points, use access point name in ARN, alias in API calls
        audit_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/{audit_s3_access_point_name or '*'}",
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/{audit_s3_access_point_name or '*'}/object/*",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        # Grant IAM permissions to file processor Lambda
        file_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                resources=[
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/{file_s3_access_point_name or '*'}/object/*",
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        file_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                resources=[
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/{output_s3_access_point_name or file_s3_access_point_name or '*'}/object/*",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        # Grant SQS permissions to file processor (will be configured with SQS trigger in later tasks)
        queue.grant_consume_messages(file_processor)
        
        # Add SQS trigger to file processor
        file_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue,
                batch_size=10,
            )
        )

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
