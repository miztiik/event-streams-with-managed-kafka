from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_msk as _msk
from aws_cdk import aws_iam as _iam
from aws_cdk import aws_ec2 as _ec2
from aws_cdk import aws_logs as _logs
from aws_cdk import core as cdk
from stacks.miztiik_global_args import GlobalArgs


class ManagedKafkaStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        stack_log_level,
        vpc,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Security Group for Managed Kafka Instance
        self.kafka_client_sg = _ec2.SecurityGroup(
            self,
            "kafkaClientSG",
            vpc=vpc,
            description="kafka client security group",
            allow_all_outbound=True,
        )
        cdk.Tags.of(self.kafka_client_sg).add("Name", "kafka_client_sg")

        self.kafka_cluster_sg = _ec2.SecurityGroup(
            self,
            "kafkaSG",
            vpc=vpc,
            security_group_name=f"kafka_sg_{construct_id}",
            description="Security Group for Kafka Cluster"
        )

        # https://docs.aws.amazon.com/msk/latest/developerguide/troubleshooting.html#networking-trouble
        self.kafka_cluster_sg.add_ingress_rule(
            peer=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=_ec2.Port.tcp(443),
            description="Allow incoming secure traffic from within VPC"
        )
        self.kafka_cluster_sg.add_ingress_rule(
            peer=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=_ec2.Port.tcp(2181),
            description="Allow incoming secure traffic from within VPC"
        )
        self.kafka_cluster_sg.add_ingress_rule(
            peer=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=_ec2.Port.tcp(9092),
            description="Allow incoming plaintext traffic REALLY from within VPC"
        )
        self.kafka_cluster_sg.add_ingress_rule(
            peer=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=_ec2.Port.tcp(9094),
            description="Allow incoming TLS-encrypted traffic from within VPC"
        )
        cdk.Tags.of(self.kafka_cluster_sg).add("Name", "kafka_cluster_sg")

        # ALLOW kafka clients to connect to kafka cluster sg
        self.kafka_cluster_sg.add_ingress_rule(
            peer=self.kafka_client_sg,
            connection=_ec2.Port.all_tcp(),
            description="ALLOW kafka clients to connect to kafka cluster sg"
        )
        # ALLOW kafka Lambda Consumer to connect to kafka cluster sg
        # https://docs.aws.amazon.com/lambda/latest/dg/services-msk-topic-add.html
        self.kafka_client_sg.add_ingress_rule(
            peer=_ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=_ec2.Port.all_tcp(),
            description="ALLOW kafka Lambda consumer to poll kafka cluster"
        )

        # Add your stack resources below):
        self.msk_cluster = _msk.CfnCluster(
            self,
            "managedKafka01",
            broker_node_group_info=_msk.CfnCluster.BrokerNodeGroupInfoProperty(
                instance_type="kafka.t3.small",
                client_subnets=vpc.select_subnets(
                    subnet_type=_ec2.SubnetType.PRIVATE
                ).subnet_ids,
                security_groups=[self.kafka_cluster_sg.security_group_id]
            ),
            cluster_name="miztiik-msk-cluster-01",
            kafka_version="2.3.1",
            number_of_broker_nodes=2
        )

        ###########################################
        ################# OUTPUTS #################
        ###########################################
        output_0 = cdk.CfnOutput(
            self,
            "AutomationFrom",
            value=f"{GlobalArgs.SOURCE_INFO}",
            description="To know more about this automation stack, check out our github page."
        )

        output_1 = cdk.CfnOutput(
            self,
            "StoreEventsKafkaRouter",
            value=f"https://console.aws.amazon.com/msk/home?region={cdk.Aws.REGION}#/clusters/{self.msk_cluster.cluster_name}",
            description="Store events Kafka Cluster"
        )
