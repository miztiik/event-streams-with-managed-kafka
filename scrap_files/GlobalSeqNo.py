import os
import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--fileName", help="fileName with consumer messages output")
args = parser.parse_args()

with open(args.fileName, "r") as file:
        for cnt, line in enumerate(file):
            msgJson = json.loads(line)
            if (cnt == 0):
                firstGlobalSeqNo = msgJson.get('globalseq')
                minGlobalSeqNo = firstGlobalSeqNo
                maxGlobalSeqNo = firstGlobalSeqNo

            if (msgJson.get('globalseq') > maxGlobalSeqNo):
                maxGlobalSeqNo = msgJson.get('globalseq')
            elif (msgJson.get('globalseq') < minGlobalSeqNo):
                minGlobalSeqNo = msgJson.get('globalseq')
            
print("Min Global Seq No in file: {0}".format(minGlobalSeqNo))
print("Max Global Seq No in file: {0}".format(maxGlobalSeqNo))
