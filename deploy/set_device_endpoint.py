from demo_badge import send_command, EXPRESSLINK_TX, EXPRESSLINK_RX
import busio
uart = busio.UART(EXPRESSLINK_TX, EXPRESSLINK_RX, baudrate=115200, receiver_buffer_size=4096, timeout=0.1)
# TODO: Enter the URL of the AWS IoT Core device data endpoint for your AWS account here. This can be found on the IoT Core settings page: https://console.aws.amazon.com/iot/home#/settings
endpoint_url=""
send_command(uart, f"AT+CONF Endpoint={endpoint_url}")
send_command(uart, "AT+CONNECT")