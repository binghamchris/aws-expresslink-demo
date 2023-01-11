import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

THING_NAME = os.environ.get("THING_NAME", "")

def lambda_handler(event, context):
  logger.debug("event:\n{}".format(json.dumps(event, indent=2)))

  try:
    client = boto3.client('iot')
    response = client.describe_endpoint(endpointType="iot:Data-ats")
    iot_endpoint = f"https://{response['endpointAddress']}"

    client = boto3.client(
      'iot-data', 
      endpoint_url=iot_endpoint
    )

    shadow = client.get_thing_shadow(
        thingName=THING_NAME
    )
  except Exception as e:
    logger.error("{}".format(e))
    return {"status": "query error", "message": "{}".format(e)} 

  return(json.loads(shadow['payload'].read())['state']['reported'])