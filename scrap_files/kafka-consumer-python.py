from kafka import KafkaConsumer
from kafka import TopicPartition
TOPIC = "test"

consumer = KafkaConsumer(bootstrap_servers='',
                          security_protocol='SSL',
                        # For TLS mutual auth:
                           ssl_check_hostname=True,
                           ssl_certfile='/tmp/client_cert.pem',
                           ssl_keyfile='/tmp/private_key.pem',
                           ssl_cafile='/tmp/truststore.pem')
                        # to generate the the truststore.pem: keytool --list -rfc -keystore /home/ec2-user/kafka240/kafka.client.truststore.jks > truststore.pem (Note: use "changeit" as password)
                        # for the trsutore copy the truststore from /etc/ssl/certs or the oracle jvm cacerts (find /usr/lib/jvm/ -name "cacerts" -exec cp {} /home/ec2-user/kafka/kafka.client.truststore.jks \;)

# Read and print all messages from test topic
parts = consumer.partitions_for_topic(TOPIC)
if parts is None:
   exit(1)
partitions = [TopicPartition(TOPIC, p) for p in parts]
consumer.assign(partitions)
for  partition in partitions:
  consumer.seek_to_beginning(partition)
for msg in consumer:
    print(msg)


