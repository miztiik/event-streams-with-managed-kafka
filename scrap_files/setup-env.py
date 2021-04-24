import boto3
import os
import sys
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--region", help="region where the Cloudformation template was run")
parser.add_argument("--stackName", help="the name of Cloudformation stack ")
args = parser.parse_args()

msk_client = boto3.client('kafka', args.region)
cf_client = boto3.client('cloudformation', args.region)
stack_name = args.stackName

def getMSKBootstrapBrokers(clusterArn):

    resp = msk_client.get_bootstrap_brokers(
    ClusterArn=clusterArn
    )
    return resp['BootstrapBrokerString']

def getMSKBootstrapBrokersTls(clusterArn):

    resp = msk_client.get_bootstrap_brokers(
    ClusterArn=clusterArn
    )
    return resp['BootstrapBrokerStringTls']

def getMSKZookeeperConnectString(clusterArn):

    resp = msk_client.describe_cluster(
    ClusterArn=clusterArn
    )
    return resp['ClusterInfo']['ZookeeperConnectString']

result = cf_client.describe_stacks(StackName=stack_name)

with open("/tmp/kafka/setup_env", "w") as f:

    for output in result['Stacks'][0]['Outputs']:
        if output['OutputKey'] == "MSKSourceClusterArn":
                cluster1Arn = output['OutputValue']
                bootstrapBrokers = getMSKBootstrapBrokers(cluster1Arn)
                bootstrapBrokersTls = getMSKBootstrapBrokersTls(cluster1Arn)
                zookeeperConnect = getMSKZookeeperConnectString(cluster1Arn)
                f.write("export brokersmsksource=" + bootstrapBrokers + "\n")
                f.write("export brokerstlsmsksource=" + bootstrapBrokersTls + "\n")
                f.write("export zoomsksource=" + zookeeperConnect + "\n")
        if output['OutputKey'] == "MSKDestinationClusterArn":
                cluster2Arn = output['OutputValue']
                bootstrapBrokers = getMSKBootstrapBrokers(cluster2Arn)
                bootstrapBrokersTls = getMSKBootstrapBrokersTls(cluster2Arn)
                zookeeperConnect = getMSKZookeeperConnectString(cluster2Arn)
                f.write("export brokersmskdest=" + bootstrapBrokers + "\n")
                f.write("export brokerstlsmskdest=" + bootstrapBrokersTls + "\n")
                f.write("export zoomskdest=" + zookeeperConnect + "\n")
        if output['OutputKey'] == "MSKClusterArn":
                clusterArn = output['OutputValue']
                bootstrapBrokers = getMSKBootstrapBrokers(clusterArn)
                bootstrapBrokersTls = getMSKBootstrapBrokersTls(clusterArn)
                zookeeperConnect = getMSKZookeeperConnectString(clusterArn)
                f.write("export brokers=" + bootstrapBrokers + "\n")
                f.write("export brokerstls=" + bootstrapBrokersTls + "\n")
                f.write("export zoo=" + zookeeperConnect + "\n")

os.chmod("/tmp/kafka/setup_env", 0o775)


