import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

THING_NAME = os.environ.get("THING_NAME", "")

def lambda_handler(event, context):
  logger.info("event:\n{}".format(json.dumps(event, indent=2)))

  try:
    client = boto3.client('iot')
    response = client.describe_endpoint(endpointType="iot:Data-ats")
    iot_endpoint = f"https://{response['endpointAddress']}"

    client = boto3.client(
      'iot-data', 
      endpoint_url=iot_endpoint
    )
    
    if event['body']:
      request = json.loads(event['body'])
    
    if request['active_button_config'] and request['active_button_config'] > 0 < 4:
      desired_state = {
        "state": {
          "desired": {
            "active_button_config": request['active_button_config']
          }
        }
      }
      shadow = client.update_thing_shadow(
        thingName=THING_NAME,
        payload=json.dumps(desired_state, indent=2).encode('utf-8')
      )

      return({"update_status":"success"})
  
  except Exception as e:
    logger.error("{}".format(e))
    return({"update_status":"failed"}) 

  return({"update_status":"failed"})