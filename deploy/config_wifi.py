from demo_badge import send_command, EXPRESSLINK_TX, EXPRESSLINK_RX
import busio
uart = busio.UART(EXPRESSLINK_TX, EXPRESSLINK_RX, baudrate=115200, receiver_buffer_size=4096, timeout=0.1)
#TODO: Enter the SSID and key for your wifi network here
wifi_ssid=""
wifi_key=""
send_command(uart, f"AT+CONF SSID={wifi_ssid}")
send_command(uart, f"AT+CONF Passphrase={wifi_key}")
