from kafka import KafkaProducer
import json
import logging
import datetime
import os
import random
import uuid


class GlobalArgs:
    OWNER = "Mystique"
    VERSION = "2021-04-19"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    STORE_EVENTS_TOPIC = os.getenv("STORE_EVENTS_TOPIC")
    KAFKA_BOOTSTRAP_SRV = os.getenv("KAFKA_BOOTSTRAP_SRV")


def set_logging(lv=GlobalArgs.LOG_LEVEL):
    logging.basicConfig(level=lv)
    logger = logging.getLogger()
    logger.setLevel(lv)
    return logger


logger = set_logging()


def _rand_coin_flip():
    r = False
    if os.getenv("TRIGGER_RANDOM_FAILURES", True):
        if random.randint(1, 100) > 90:
            r = True
    return r


def _gen_uuid():
    return str(uuid.uuid4())


def send_to_kafka(_t, data):
    try:
        producer = KafkaProducer(
            security_protocol="SSL",
            retry_backoff_ms=500,
            request_timeout_ms=20000,
            bootstrap_servers=GlobalArgs.KAFKA_BOOTSTRAP_SRV,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        _f = producer.send(_t, data)
        producer.flush()
        _r = _f.get(timeout=10)
        logger.info(
            f"{_r.topic} :{_r.partition} :{_r.offset}")
    except Exception as e:
        logger.exception(f"ERROR:{str(e)}")


def lambda_handler(event, context):
    resp = {"status": False}
    logger.debug(f"Event: {json.dumps(event)}")
    _categories = ["Books", "Games", "Mobiles", "Groceries", "Shoes", "Stationaries", "Laptops",
                   "Tablets", "Notebooks", "Camera", "Printers", "Monitors", "Speakers", "Projectors", "Cables", "Furniture"]
    _evnt_types = ["sale_event", "inventory_event"]

    try:
        t_msgs = 0
        p_cnt = 0
        s_evnts = 0
        inventory_evnts = 0
        t_sales = 0
        while True:
            _s = round(random.random() * 100, 2)
            _evnt_type = random.choice(_evnt_types)
            _u = _gen_uuid()
            p_s = bool(random.getrandbits(1))
            evnt_body = {
                "request_id": _u,
                "category": random.choice(_categories),
                "store_id": random.randint(1, 10),
                "ts": datetime.datetime.now().isoformat(),
                "event_type": _evnt_type,
                "sales": _s,
                "sku": random.randint(18981, 189281),
                "gift_wrap": bool(random.getrandbits(1)),
                "qty": random.randint(1, 38),
                "priority_shipping": p_s,
                "contact_me": "github.com/miztiik"
            }
            evnt_attr = {
                "evnt_type": {
                    "DataType": "String",
                    "StringValue": _evnt_type
                },
                "priority_shipping": {
                    "DataType": "String",
                    "StringValue": f"{p_s}"
                }
            }

            # Make the order type as return
            if bool(random.getrandbits(1)):
                evnt_body["is_return"] = True

            if _rand_coin_flip():
                evnt_body.pop("store_id", None)
                evnt_body["bad_msg"] = True
                p_cnt += 1

            if _evnt_type == "sale_event":
                s_evnts += 1
            elif _evnt_type == "inventory_event":
                inventory_evnts += 1

            send_to_kafka(
                GlobalArgs.STORE_EVENTS_TOPIC,
                evnt_body
            )
            t_msgs += 1
            t_sales += _s
            if context.get_remaining_time_in_millis() < 1000:
                break

        resp["tot_msgs"] = t_msgs
        resp["bad_msgs"] = p_cnt
        resp["sale_evnts"] = s_evnts
        resp["inventory_evnts"] = inventory_evnts
        resp["tot_sales"] = t_sales
        resp["status"] = True
        logger.info(f'{{"resp":{json.dumps(resp)}}}')

    except Exception as e:
        logger.error(f"ERROR:{str(e)}")
        resp["err_msg"] = str(e)

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": resp
        })
    }
