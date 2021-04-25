#!/usr/bin/env python3

from aws_cdk import core as cdk

from stacks.back_end.vpc_stack import VpcStack
from stacks.back_end.s3_stack.s3_stack import S3Stack
from stacks.back_end.kakfa_admin_on_ec2_stack.kakfa_admin_on_ec2_stack import KafkaAdminOnEC2Stack
from stacks.back_end.serverless_kafka_consumer_stack.serverless_kafka_consumer_stack import ServerlessKafkaConsumerStack
from stacks.back_end.msk_stack.msk_stack import ManagedKafkaStack
from stacks.back_end.serverless_kafka_producer_stack.serverless_kafka_producer_stack import ServerlessKafkaProducerStack


app = cdk.App()

# S3 Bucket to hold our sales events
sales_events_bkt_stack = S3Stack(
    app,
    # f"{app.node.try_get_context('project')}-sales-events-bkt-stack",
    f"sales-events-bkt-stack",
    stack_log_level="INFO",
    description="Miztiik Automation: S3 Bucket to hold our sales events"
)

# VPC Stack for hosting Secure workloads & Other resources
vpc_stack = VpcStack(
    app,
    f"{app.node.try_get_context('project')}-vpc-stack",
    stack_log_level="INFO",
    description="Miztiik Automation: Custom Multi-AZ VPC"
)

# Workstation to interact with the resources
# admin_workstation_stack = Cloud9Stack(
#     app,
#     f"cloud9-admin-workstation-stack",
#     stack_log_level="INFO",
#     vpc=vpc_stack.vpc,
#     description="Miztiik Automation: Workstation to interact with the resources"
# )

# Managed Kafka Stack
managed_kafka_stack = ManagedKafkaStack(
    app,
    "sales-events-kafka-stack",
    stack_log_level="INFO",
    vpc=vpc_stack.vpc,
    description="Miztiik Automation: Managed Kafka Stack"
)

# Kafka Admin On EC2 instance
kakfa_admin_on_ec2_stack = KafkaAdminOnEC2Stack(
    app,
    f"kafka-admin-on-ec2-stack",
    stack_log_level="INFO",
    vpc=vpc_stack.vpc,
    ec2_instance_type="t2.micro",
    kafka_cluster=managed_kafka_stack.msk_cluster,
    description="Miztiik Automation: Kafka Admin On EC2 instance"
)

# S3 Sales Event Data Producer on Lambda
sales_events_producer_stack = ServerlessKafkaProducerStack(
    app,
    f"sales-events-producer-stack",
    stack_log_level="INFO",
    vpc=vpc_stack.vpc,
    kafka_client_sg=managed_kafka_stack.kafka_client_sg,
    kafka_topic_name="MystiqueStoreEventsTopic",
    description="Miztiik Automation: S3 Sales Event Data Producer on Lambda")

# Consume messages from Kafka
sales_events_consumer_stack = ServerlessKafkaConsumerStack(
    app,
    # f"{app.node.try_get_context('project')}-orders-consumer-stack",
    f"sales-events-consumer-stack",
    stack_log_level="INFO",
    kafka_cluster=managed_kafka_stack.msk_cluster,
    kafka_topic_name="MystiqueStoreEventsTopic",
    sales_event_bkt=sales_events_bkt_stack.data_bkt,
    description="Miztiik Automation: Consume Customer Order Events Messages"
)

# Stack Level Tagging
_tags_lst = app.node.try_get_context("tags")

if _tags_lst:
    for _t in _tags_lst:
        for k, v in _t.items():
            cdk.Tags.of(app).add(
                k, v, apply_to_launched_instances=True, priority=300)

app.synth()
