from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_ec2 as _ec2
from aws_cdk import aws_logs as _logs
from aws_cdk import core as cdk
from stacks.miztiik_global_args import GlobalArgs


class ServerlessKafkaConsumerStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level: str,
        vpc,
        kafka_client_sg,
        sales_event_bkt,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add your stack resources below):

        ########################################
        #######                          #######
        #######   Stream Data Consumer   #######
        #######                          #######
        ########################################

        # Lambda Execution Role
        # https://docs.aws.amazon.com/lambda/latest/dg/lambda-intro-execution-role.html
        _lambda_exec_role = _iam.Role(
            self,
            "lambdaExecRole",
            assumed_by=_iam.ServicePrincipal(
                "lambda.amazonaws.com"),
            managed_policies=[
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaMSKExecutionRole"
                ),
                _iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaVPCAccessExecutionRole"
                )
            ]
        )

        # Read Lambda Code
        try:
            with open("stacks/back_end/serverless_kafka_consumer_stack/lambda_src/serverless_kafka_consumer.py",
                      encoding="utf-8",
                      mode="r"
                      ) as f:
                msg_consumer_fn_code = f.read()
        except OSError:
            print("Unable to read Lambda Function Code")
            raise
        msg_consumer_fn = _lambda.Function(
            self,
            "msgConsumerFn",
            function_name=f"store_events_consumer_fn",
            description="Process messages in Kafka Topic",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.InlineCode(
                msg_consumer_fn_code),
            handler="index.lambda_handler",
            timeout=cdk.Duration.seconds(5),
            reserved_concurrent_executions=1,
            environment={
                "LOG_LEVEL": f"{stack_log_level}",
                "APP_ENV": "Production",
                "TRIGGER_RANDOM_DELAY": "True",
                "STORE_EVENTS_BKT": f"{sales_event_bkt.bucket_name}"
            },
            role=_lambda_exec_role,
            # layers=[kafka_layer],
            # security_group=kafka_client_sg,
            # vpc=vpc,
            # vpc_subnets=_ec2.SubnetType.PRIVATE
        )

        msg_consumer_fn_version = msg_consumer_fn.latest_version
        msg_consumer_fn_version_alias = _lambda.Alias(
            self,
            "msgConsumerFnAlias",
            alias_name="MystiqueAutomation",
            version=msg_consumer_fn_version
        )

        # Create Custom Loggroup for Producer
        msg_consumer_fn_lg = _logs.LogGroup(
            self,
            "msgConsumerFnLogGroup",
            log_group_name=f"/aws/lambda/{msg_consumer_fn.function_name}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            retention=_logs.RetentionDays.ONE_DAY
        )

        # Restrict Produce Lambda to be invoked only from the stack owner account
        msg_consumer_fn.add_permission(
            "restrictLambdaInvocationToOwnAccount",
            principal=_iam.AccountRootPrincipal(),
            action="lambda:InvokeFunction",
            source_account=cdk.Aws.ACCOUNT_ID,
            # source_arn=orders_bus.event_bus_arn
        )

        sales_event_bkt.grant_read_write(msg_consumer_fn)

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )

        output_2 = cdk.CfnOutput(
            self,
            "msgConsumer",
            value=f"https://console.aws.amazon.com/lambda/home?region={cdk.Aws.REGION}#/functions/{msg_consumer_fn.function_name}",
            description="Process events received from eventbridge event bus"
        )
