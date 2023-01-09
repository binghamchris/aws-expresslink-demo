# Demo Deployment
These files can be used to setup this demo on an AWS IoT ExpressLink Demo Badge. Please note that this specific hardware is required in order to use this demo, and assumes that the AWS-provided default libraries are still present of the Demo Badges internal memory.

## Deployment Process
There are four steps needed to deploy the demo:
1. Configure the wifi connection on the Demo Badge
2. Get the certificate and device name information from the Demo Badge
3. Deploy the CloudFormation template to your AWS account, providing the parameters retrieved in step 2
4. Configure the AWS IoT Core endpoint on the Demo Badge
5. Create a classic shadow for the Demo Badge

### 1. Configure the wifi connection on the Demo Badge
Enter your wifi network's SSID and key into the variables `wifi_ssid` and `wifi_key` respectively in the file `config_wifi.py`. Afterwards this file should be treated as highly security sensitive, seeing as it now contains a security token (your wifi network's key), so please take all necessary precautions about saving or disseminating it, and most especially avoid accidentally committing it to your Git repo!

Connect to your Demo Badge over the USB-C connection using a serial console, such as the [serial-terminal web app](https://googlechromelabs.github.io/serial-terminal/), then copy and paste the commands from the file `config_wifi.py` into the console.

If the two `send_command` lines return the response `OK`, the configuration was completed successfully.

### 2. Get the certificate and device name information from the Demo Badge
Connect to your Demo Badge over the USB-C connection using a serial console, such as the [serial-terminal web app](https://googlechromelabs.github.io/serial-terminal/), then copy and paste the commands from the file `get_device_cert.py` into the console.

This should output both the devices certificate in PEM format and its device name, both of which will be needed in the next step.

### 3. Deploy the CloudFormation template to your AWS account, providing the parameters retrieved in step two
In your AWS account, deploy the CloudFormation template `demo_deploy.yaml`, providing the following parameters:
- `ExpressLinkCertPem`: Enter the main body of the certificate displayed in the serial console during step two, without the "BEGIN CERTIFICATE" and "END CERTIFICATE" lines. These lines will be added back in by the template, as a workaround for the lack of multi-line sting support in parameters in CloudFormation.
- `ExpressLinkThingName`: Enter the device name displayed in the serial console during step two.

This will create the AWS resources needed for the demo badge to connect to AWS IoT Core. Please review the CloudFormation template for information about these resources.

### 4. Configure the AWS IoT Core endpoint on the Demo Badge
Enter your AWS account's "device data endpoint" URL into the variable `endpoint_url` in the file `set_device_endpoint.py`. This URL can be found on the [AWS IoT Core settings page](https://console.aws.amazon.com/iot/home#/settings).

Connect to your Demo Badge over the USB-C connection using a serial console, such as the [serial-terminal web app](https://googlechromelabs.github.io/serial-terminal/), then copy and paste the commands from the file `set_device_endpoint.py` into the console.

The Demo Badge should immediately attempt to connect to AWS IoT Core. If the attempt is successful, the message `OK 1 CONNECTED` will be displayed in the serial console.

### 5. Create a classic shadow for the Demo Badge
In the AWS IoT console navigate to "All devices > Things" and select the thing with the device name displayed in the serial console during step two.
Under the "Device Shadows" tab, selected "Create Shadow" and create a new "Classic (unnamed)" shadow.