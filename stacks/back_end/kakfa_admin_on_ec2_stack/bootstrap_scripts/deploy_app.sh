#!/bin/bash
set -ex
set -o pipefail

# VERSION: 2021-04-25

##################################################
#############     SET GLOBALS     ################
##################################################

REPO_NAME="event-streams-with-managed-kafka"

GIT_REPO_URL="https://github.com/miztiik/$REPO_NAME.git"

APP_DIR="/var/$REPO_NAME"

LOG_FILE="/var/log/miztiik-automation-bootstrap.log"

APP_LOG_FILE="/var/log/miztiik-automation-app-kafka.log"

userdata_troubleshooting(){
    USER_DATA_SCRIPT_LOC="/var/lib/cloud/instances/"
}

instruction()
{
  echo "usage: ./build.sh package <stage> <region>"
  echo ""
  echo "/build.sh deploy <stage> <region> <pkg_dir>"
  echo ""
  echo "/build.sh test-<test_type> <stage>"
}

assume_role() {
  if [ -n "$DEPLOYER_ROLE_ARN" ]; then
    echo "Assuming role $DEPLOYER_ROLE_ARN ..."
    CREDS=$(aws sts assume-role --role-arn $DEPLOYER_ROLE_ARN \
        --role-session-name my-sls-session --out json)
    echo $CREDS > temp_creds.json
    export AWS_ACCESS_KEY_ID=$(node -p "require('./temp_creds.json').Credentials.AccessKeyId")
    export AWS_SECRET_ACCESS_KEY=$(node -p "require('./temp_creds.json').Credentials.SecretAccessKey")
    export AWS_SESSION_TOKEN=$(node -p "require('./temp_creds.json').Credentials.SessionToken")
    aws sts get-caller-identity
  fi
}

unassume_role() {
  unset AWS_ACCESS_KEY_ID
  unset AWS_SECRET_ACCESS_KEY
  unset AWS_SESSION_TOKEN
}

function clone_git_repo(){
    install_libs
    # mkdir -p /var/
    cd /var
    git clone $GIT_REPO_URL

}

function add_env_vars(){
    EC2_AVAIL_ZONE=`curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone`
    AWS_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"
    export AWS_REGION
    #setup bash env
    su -c "echo 'export PS1=\"MiztiikKafkaAdmin01 [\u@\h \W\\]$ \"' >> /home/ec2-user/.bash_profile" -s /bin/sh ec2-user
    # su -c "echo '[ -f /var/kafka/setup_env ] && . /var/kafka/setup_env' >> /home/ec2-user/.bash_profile" -s /bin/sh ec2-user
}

function install_libs(){
    # Prepare the server for python3
    yum -y install python-pip python3 git
    yum install -y jq
    pip3 install boto3
}

function install_nodejs(){
    # https://docs.aws.amazon.com/sdk-for-javascript/v2/developer-guide/setting-up-node-on-ec2-instance.html
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
    . ~/.nvm/nvm.sh
    nvm install node
    node -e "console.log('Running Node.js ' + process.version)"
}

function install_xray(){
    # Install AWS XRay Daemon for telemetry
    curl https://s3.dualstack.us-east-2.amazonaws.com/aws-xray-assets.us-east-2/xray-daemon/aws-xray-daemon-3.x.rpm -o /home/ec2-user/xray.rpm
    yum install -y /home/ec2-user/xray.rpm
}

function install_kafka(){
    cd /home/ec2-user
    echo "export PATH=.local/bin:$PATH" >> .bash_profile

    # Begin kafka installation
    KAFKA_DIR="kafka"
    rm -rf /var/${KAFKA_DIR}
    mkdir -p /var/${KAFKA_DIR}
    cd /var/${KAFKA_DIR}
    # sudo yum -y install java-1.8.0-openjdk-devel
    # sudo yum install java-1.8.0 -y
    pip3 install kafka-python
    sudo yum install -y java
    java --version

    wget https://archive.apache.org/dist/kafka/2.2.1/kafka_2.12-2.2.1.tgz
    tar -xzf kafka_2.12-2.2.1.tgz --strip 1

}

function configure_kafka_topic(){
cd /var/kafka/
EC2_AVAIL_ZONE=`curl -s http://169.254.169.254/latest/meta-data/placement/availability-zone`
AWS_REGION="`echo \"$EC2_AVAIL_ZONE\" | sed 's/[a-z]$//'`"

export AWS_REGION

# Setup up Trust certificate in client properites
find /usr/lib/jvm/ -name "cacerts" -exec cp {} /var/kafka/kafka.client.truststore.jks \;
cat > '/var/kafka/client.properties' << "EOF"
security.protocol=SSL
ssl.truststore.location=/var/kafka/kafka.client.truststore.jks
EOF

# Get Cluster Details
KAFKA_CLUSTER_NAME="miztiik-msk-cluster-01"
STORE_EVENTS_TOPIC="MystiqueStoreEventsTopic"

KAFKA_CLUSTER_ARN=`aws kafka list-clusters --region ${AWS_REGION} --cluster-name-filter ${KAFKA_CLUSTER_NAME} --output text --query 'ClusterInfoList[*].ClusterArn'`
KAFKA_ZOOKEEPER=`aws kafka describe-cluster --cluster-arn ${KAFKA_CLUSTER_ARN} --region ${AWS_REGION} --output text --query 'ClusterInfo.ZookeeperConnectString'`
BOOTSTRAP_BROKER_SRV=`aws kafka get-bootstrap-brokers --region ${AWS_REGION} --cluster-arn ${KAFKA_CLUSTER_ARN} --output text --query 'BootstrapBrokerStringTls'`

echo ${KAFKA_CLUSTER_NAME}
echo ${KAFKA_CLUSTER_ARN}
echo ${KAFKA_ZOOKEEPER}
echo ${STORE_EVENTS_TOPIC}
echo ${BOOTSTRAP_BROKER_SRV}

echo -e "Creating topic ${STORE_EVENTS_TOPIC}"
./bin/kafka-topics.sh --create --zookeeper ${KAFKA_ZOOKEEPER} --replication-factor 2 --partitions 2 --topic ${STORE_EVENTS_TOPIC}

#  ./bin/kafka-console-producer.sh --broker-list ${BOOTSTRAP_BROKER_SRV} --producer.config /var/kafka/client.properties --topic  ${STORE_EVENTS_TOPIC}
#  ./bin/kafka-console-consumer.sh --bootstrap-server ${BOOTSTRAP_BROKER_SRV} --consumer.config /var/kafka/client.properties --topic  ${STORE_EVENTS_TOPIC} --from-beginning
}

function install_cw_agent() {
# Installing AWS CloudWatch Agent FOR AMAZON LINUX RPM
agent_dir="/tmp/cw_agent"
cw_agent_rpm="https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm"
mkdir -p ${agent_dir} \
    && cd ${agent_dir} \
    && sudo yum install -y curl \
    && curl ${cw_agent_rpm} -o ${agent_dir}/amazon-cloudwatch-agent.rpm \
    && sudo rpm -U ${agent_dir}/amazon-cloudwatch-agent.rpm


cw_agent_schema="/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json"

# PARAM_NAME="/stream-data-processor/streams/data_pipe/stream_name"
# a=$(aws ssm get-parameter --name "$PARAM_NAME" --with-decryption --query "Parameter.{Value:Value}" --output text)
# LOG_GROUP_NAME="/stream-data-processor/producers"

cat > '/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json' << "EOF"
{
"agent": {
    "metrics_collection_interval": 5,
    "logfile": "/opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log"
},
"metrics": {
    "metrics_collected": {
    "mem": {
        "measurement": [
        "mem_used_percent"
        ]
    }
    },
    "append_dimensions": {
    "ImageId": "${aws:ImageId}",
    "InstanceId": "${aws:InstanceId}",
    "InstanceType": "${aws:InstanceType}"
    },
    "aggregation_dimensions": [
    [
        "InstanceId",
        "InstanceType"
    ],
    []
    ]
},
"logs": {
    "logs_collected": {
    "files": {
        "collect_list": [
        {
            "file_path": "/var/log/miztiik-automation-app**.json",
            "log_group_name": "/miztiik-automation/apps/",
            "log_stream_name":"mysql-client-logs",
            "timestamp_format": "%b %-d %H:%M:%S",
            
            "timezone": "Local"
        },
        {
            "file_path": "/var/log/miztiik-automation-app**.log",
            "log_group_name": "/miztiik-automation/apps/",
            "log_stream_name":"app-logs",
            "timestamp_format": "%b %-d %H:%M:%S",
            "timezone": "Local"
        },
        {
            "file_path": "/var/log/miztiik-automation-bootstrap.log",
            "log_group_name": "/miztiik-automation/bootstrap/",
            "timestamp_format": "%b %-d %H:%M:%S",
            "timezone": "Local"
        }
        ]
    }
    },
    "log_stream_name": "{instance_id}"
}
}
EOF

    # Configure the agent to monitor ssh log file
    sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:${cw_agent_schema} -s
    # Start the CW Agent
    sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status

    # Just in case we need to troubleshoot
    # cd "/opt/aws/amazon-cloudwatch-agent/logs/"
}

# Let the execution begin
# if [ $# -eq 0 ]; then
#   instruction
#   exit 1

install_libs                | tee "${LOG_FILE}"
install_cw_agent            | tee "${LOG_FILE}"
install_kafka               | tee "${LOG_FILE}"
configure_kafka_topic       | tee "${APP_LOG_FILE}"
