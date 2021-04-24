# -*- coding: utf-8 -*-

import base64
import datetime
import json
import logging
import os
import random


class GlobalArgs:
    OWNER = "Mystique"
    VERSION = "2021-04-19"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    S3_BKT_NAME = os.getenv("STORE_EVENTS_BKT")
    S3_PREFIX = "store_events"


def set_logging(lv=GlobalArgs.LOG_LEVEL):
    """ Helper to enable logging """
    logging.basicConfig(level=lv)
    logger = logging.getLogger()
    logger.setLevel(lv)
    return logger


LOG = set_logging()
kafka_client = None
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def _rand_coin_flip():
    r = False
    if os.getenv("TRIGGER_RANDOM_DELAY", True):
        if random.randint(1, 100) > 90:
            r = True
    return r


def put_object(_pre, data):
    try:
        _r = _s3.put_object(
            Bucket=GlobalArgs.S3_BKT_NAME,
            Key=f"event_type={_pre}/dt={datetime.datetime.now().strftime('%Y_%m_%d')}/{datetime.datetime.now().strftime('%s%f')}.json",
            Body=json.dumps(data).encode("UTF-8"),
        )
        logger.debug(f"resp: {json.dumps(_r)}")
    except Exception as e:
        logger.exception(f"ERROR:{str(e)}")


def base64ToString(b):
    return base64.b64decode(b).decode("utf-8")


_s3 = boto3.client("s3")


def lambda_handler(event, context):
    resp = {"status": False}
    LOG.info(f"Event: {json.dumps(event)}")
    try:

        if event.get("records"):
            for _key, _val in event.get("records").items():
                topic_partition = _key
                LOG.info(f"topic_partition: {topic_partition}")
                for msg in event.get("records")[topic_partition]:
                    for k, v in msg.items():
                        LOG.info(f"{k}: {v}")
                    LOG.info(
                        {base64ToString(msg["value"])}
                    )
                # Writing Events To S3
                put_object(
                    _evnt_type,
                    evnt_body
                )

        resp["status"] = True

        LOG.info(f'{{"resp":{json.dumps(resp)}}}')

    except Exception as e:
        logger.error(f"ERROR:{str(e)}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": resp
        })
    }
