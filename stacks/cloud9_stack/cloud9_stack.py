from aws_cdk import aws_cloud9 as _cloud9
from aws_cdk import aws_iam as _iam
from aws_cdk import core as cdk
from stacks.miztiik_global_args import GlobalArgs


class Cloud9Stack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level,
        vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Add your stack resources below):
        cloud9_instance = _cloud9.CfnEnvironmentEC2(
            self,
            "Cloud9Instance",
            name="MiztiikWorkstation",
            description="Workstation to interact with the resources",
            instance_type="t2.micro",
            connection_type="CONNECT_SSM",
            # owner_arn=_iam.AccountRootPrincipal(cdk.Aws.ACCOUNT_ID),
            # owner_arn=f"{_iam.ArnPrincipal(cdk.Aws.ACCOUNT_ID)}",
            owner_arn=f"{_iam.AccountRootPrincipal().arn}",
            automatic_stop_time_minutes=60,
            subnet_id=vpc.public_subnets[0].subnet_id,
            # repositories=[cloud9_repository]
        )
        cloud9_instance.apply_removal_policy(cdk.RemovalPolicy.DESTROY)



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
            "Cloud9Workstation",
            value=f"{cloud9_instance.attr_name}",
            description="Cloud9 Workstation.",
        )
        output_2 = cdk.CfnOutput(
            self,
            "Cloud9WorkstationUrl",
            value=f"https://{cdk.Aws.REGION}.console.aws.amazon.com/cloud9/home/environments/{cloud9_instance.ref}?permissions=owner",
            description="Cloud9 Workstation Url, Use this URL to access your Cloud9 IDE in a browser",
        )
