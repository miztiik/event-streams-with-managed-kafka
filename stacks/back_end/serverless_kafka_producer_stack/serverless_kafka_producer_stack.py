from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_logs as _logs
from aws_cdk import aws_ec2 as _ec2
from aws_cdk import core as cdk
from stacks.miztiik_global_args import GlobalArgs


class ServerlessKafkaProducerStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level: str,
        vpc,
        kafka_client_sg,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add your stack resources below):

        ########################################
        #######                          #######
        #######   Stream Data Producer   #######
        #######                          #######
        ########################################

        # Create AWS Kafka Layer
        kafka_layer = _lambda.LayerVersion(
            self,
            "kafkaLayer",
            code=_lambda.Code.from_asset(
                "stacks/back_end/serverless_kafka_producer_stack/lambda_src/layer_code/kafka_python3.zip"),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_7,
                _lambda.Runtime.PYTHON_3_8
            ],
            license=f"Mystique Lambda Layer of kafka, Refer to AWS for license.",
            description="Layer to for latest version of kafka"
        )

        # Read Lambda Code
        try:
            with open(
                "stacks/back_end/serverless_kafka_producer_stack/lambda_src/stream_data_producer.py",
                encoding="utf-8",
                mode="r",
            ) as f:
                data_producer_fn_code = f.read()
        except OSError:
            print("Unable to read Lambda Function Code")
            raise

        data_producer_fn = _lambda.Function(
            self,
            "streamDataProducerFn",
            function_name=f"data_producer_{construct_id}",
            description="Produce streaming data events and push to Kafka Topic",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.InlineCode(data_producer_fn_code),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(10),
            reserved_concurrent_executions=1,
            environment={
                "LOG_LEVEL": "INFO",
                "APP_ENV": "Production",
                "TRIGGER_RANDOM_DELAY": "True",
                "STORE_EVENTS_TOPIC": "MystiqueStoreEventsTopic",
                "KAFKA_BOOTSTRAP_SRV": "",
                "LD_LIBRARY_PATH": "/opt/python"
            },
            layers=[kafka_layer],
            security_group=kafka_client_sg,
            vpc=vpc,
            vpc_subnets=_ec2.SubnetType.PRIVATE
        )

        # Grant our Lambda Producer privileges to write to S3
        # sales_event_bkt.grant_read_write(data_producer_fn)

        data_producer_fn_version = data_producer_fn.latest_version
        data_producer_fn_version_alias = _lambda.Alias(
            self,
            "streamDataProducerFnAlias",
            alias_name="MystiqueAutomation",
            version=data_producer_fn_version,
        )

        # Create Custom Loggroup for Producer
        data_producer_lg = _logs.LogGroup(
            self,
            "streamDataProducerFnLogGroup",
            log_group_name=f"/aws/lambda/{data_producer_fn.function_name}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            retention=_logs.RetentionDays.ONE_DAY,
        )

        # Restrict Produce Lambda to be invoked only from the stack owner account
        data_producer_fn.add_permission(
            "restrictLambdaInvocationToOwnAccount",
            principal=_iam.AccountRootPrincipal(),
            action="lambda:InvokeFunction",
            source_account=cdk.Aws.ACCOUNT_ID,
            # source_arn=sales_event_bkt.bucket_arn
        )

        # https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
        roleStmt1 = _iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=['*'],
            actions=['ec2:CreateNetworkInterface',
                     'ec2:DescribeNetworkInterfaces',
                     'ec2:DeleteNetworkInterface']
        )
        roleStmt1.sid = "AllowLambdaToManageVPCENI"
        data_producer_fn.add_to_role_policy(roleStmt1)

        ###########################################
        ################# OUTPUTS #################
        ###########################################

        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page.",
        )

        output_1 = cdk.CfnOutput(
            self,
            "SaleOrderEventsProducer",
            value=f"https://console.aws.amazon.com/lambda/home?region={cdk.Aws.REGION}#/functions/{data_producer_fn.function_name}",
            description="Produce streaming data events and push to S3 Topic.",
        )
