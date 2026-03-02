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

from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    RemovalPolicy,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_logs as logs,
    aws_events as events,
    aws_lambda as lambda_,
    aws_lambda_destinations as destinations,
    aws_events_targets as targets,
    aws_lambda_event_sources as lambda_event_sources,
    aws_iam as iam,
)
from constructs import Construct
import json
import os


class FsxAuditStack(Stack):
    """
    CDK Stack for FSx ONTAP Audit Event Processing.
    
    Core deployment (always):
    - DynamoDB table for checkpoint tracking
    - EventBridge event bus for file events
    - Lambda function for audit log processing
    - EventBridge schedule for triggering audit processor
    
    Example deployment (optional, deploy_example=True):
    - SQS queue for file events
    - Lambda function for thumbnail generation
    - EventBridge rule routing events to SQS
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        audit_s3_access_point_alias: str = None,
        file_s3_access_point_alias: str = None,
        output_s3_access_point_alias: str = None,
        lambda_path: str = "../lambda",
        layers_path: str = "../layers",
        audit_prefix: str = "",
        deploy_example: bool = False,
        routing_config_path: str = None,
        event_types_config: dict = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Default event types: create + delete enabled, modify/read/rename disabled
        if event_types_config is None:
            event_types_config = {
                'create': True,
                'delete': True,
                'modify': False,
                'read': False,
                'rename': False
            }

        # Load routing config if provided
        routing_config = None
        if routing_config_path and os.path.exists(routing_config_path):
            with open(routing_config_path, encoding='utf-8') as f:
                routing_config = json.load(f)

        # ============================================================
        # CORE RESOURCES (always deployed)
        # ============================================================

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

        # Lambda failure DLQ for audit processor
        lambda_dlq = sqs.Queue(
            self,
            "AuditProcessorDLQ",
            retention_period=Duration.days(14),
        )

        # EventBridge Event Bus for file events
        event_bus = events.EventBus(
            self,
            "FileEventsEventBus",
            event_bus_name=f"{construct_id}-file-events",
        )

        # ============================================================
        # ROUTING RESOURCES (created based on routing_config)
        # ============================================================
        
        if routing_config:
            for route in routing_config.get('routes', []):
                svm = route.get('svm_name', '')
                jp = route.get('junction_path', '')
                dest_type = route.get('destination_type', '')
                
                if not route.get('destination_arn') and svm and jp and dest_type:
                    resource_name = f"{svm}-{jp}".replace('_', '-').replace('/', '-')
                    
                    if dest_type == 'sqs':
                        q = sqs.Queue(self, f"Route-{resource_name}-Queue",
                            queue_name=f"{construct_id}-{svm}-{jp}-queue".replace('_', '-'),
                            retention_period=Duration.days(4))
                        route['destination_arn'] = q.queue_url
                        
                    elif dest_type == 'sns':
                        t = sns.Topic(self, f"Route-{resource_name}-Topic",
                            topic_name=f"{construct_id}-{svm}-{jp}-topic".replace('_', '-'))
                        route['destination_arn'] = t.topic_arn
                        
                    elif dest_type == 'cloudwatch_logs':
                        lg = logs.LogGroup(self, f"Route-{resource_name}-LogGroup",
                            log_group_name=f"/fsx/{construct_id}/{svm}/{jp}",
                            retention=logs.RetentionDays.ONE_MONTH,
                            removal_policy=RemovalPolicy.DESTROY)
                        route['destination_arn'] = lg.log_group_name

        # EVTX Lambda layer (required for audit processing)
        evtx_layer = lambda_.LayerVersion(
            self,
            "EvtxLayer",
            code=lambda_.Code.from_asset(f"{layers_path}/evtx"),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="python-evtx library for EVTX parsing",
        )

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
                "EVENT_BUS_NAME": event_bus.event_bus_name,
                "ROUTING_CONFIG": json.dumps(routing_config) if routing_config else "",
                "EVENT_TYPES_CONFIG": json.dumps(event_types_config),
                "MAX_KEYS": "100",
                "MAX_LOGS_PER_INVOCATION": "10",
            },
            on_failure=destinations.SqsDestination(lambda_dlq),
        )

        # EventBridge schedule rule (every 1 minute)
        schedule_rule = events.Rule(
            self,
            "AuditProcessorSchedule",
            schedule=events.Schedule.rate(Duration.minutes(1)),
        )
        schedule_rule.add_target(targets.LambdaFunction(audit_processor))

        # Grant IAM permissions to audit processor
        state_table.grant_read_write_data(audit_processor)
        event_bus.grant_put_events_to(audit_processor)

        # Grant S3 permissions for audit log access (use wildcard for access points)
        audit_processor.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/*",
                    f"arn:aws:s3:{self.region}:{self.account}:accesspoint/*/object/*",
                ],
                effect=iam.Effect.ALLOW,
            )
        )

        # Grant permissions for routing destinations
        if routing_config:
            audit_processor.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["sqs:SendMessage", "sqs:SendMessageBatch"],
                    resources=[f"arn:aws:sqs:{self.region}:{self.account}:*"],
                    effect=iam.Effect.ALLOW,
                )
            )
            audit_processor.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["sns:Publish"],
                    resources=[f"arn:aws:sns:{self.region}:{self.account}:*"],
                    effect=iam.Effect.ALLOW,
                )
            )
            audit_processor.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["logs:CreateLogStream", "logs:PutLogEvents"],
                    resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/fsx/*"],
                    effect=iam.Effect.ALLOW,
                )
            )

        # ============================================================
        # EXAMPLE RESOURCES (optional - thumbnail generation demo)
        # ============================================================

        if deploy_example:
            # SQS Dead Letter Queue for file events
            dlq = sqs.Queue(
                self,
                "FileEventsDLQ",
                retention_period=Duration.days(14),
            )

            # SQS Main Queue for file events
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

            # EventBridge rule to route events to SQS
            file_events_rule = events.Rule(
                self,
                "FileEventsToSQS",
                event_bus=event_bus,
                event_pattern=events.EventPattern(
                    source=["fsx.ontap.audit"],
                    detail_type=["File Event"],
                ),
            )
            file_events_rule.add_target(targets.SqsQueue(queue))

            # Pillow Lambda layer for image processing
            pillow_layer = lambda_.LayerVersion(
                self,
                "PillowLayer",
                code=lambda_.Code.from_asset(f"{layers_path}/pillow"),
                compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
                description="Pillow library for image processing",
            )

            # File Processor Lambda (thumbnail generation)
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

            # Grant S3 permissions to file processor (use wildcard for access points)
            file_processor.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["s3:GetObject"],
                    resources=[
                        f"arn:aws:s3:{self.region}:{self.account}:accesspoint/*/object/*",
                    ],
                    effect=iam.Effect.ALLOW,
                )
            )
            file_processor.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["s3:PutObject"],
                    resources=[
                        f"arn:aws:s3:{self.region}:{self.account}:accesspoint/*/object/*",
                    ],
                    effect=iam.Effect.ALLOW,
                )
            )

            # SQS trigger for file processor
            queue.grant_consume_messages(file_processor)
            file_processor.add_event_source(
                lambda_event_sources.SqsEventSource(queue, batch_size=10)
            )

            # Example outputs
            CfnOutput(self, "QueueUrl", value=queue.queue_url,
                      description="SQS queue URL for file events (example)")
            CfnOutput(self, "DLQArn", value=dlq.queue_arn,
                      description="Dead letter queue ARN (example)")

            # Store example references
            self.queue = queue
            self.file_processor = file_processor

        # ============================================================
        # STACK OUTPUTS (core)
        # ============================================================

        CfnOutput(self, "StateTableName", value=state_table.table_name,
                  description="DynamoDB state table name")
        CfnOutput(self, "EventBusName", value=event_bus.event_bus_name,
                  description="EventBridge event bus name")
        CfnOutput(self, "LambdaDLQArn", value=lambda_dlq.queue_arn,
                  description="Lambda failure dead letter queue ARN")
        CfnOutput(self, "AuditS3AccessPointAlias",
                  value=audit_s3_access_point_alias or "NOT_SET",
                  description="S3 Access Point alias for audit logs")

        # Store core references
        self.state_table = state_table
        self.event_bus = event_bus
        self.audit_processor = audit_processor
