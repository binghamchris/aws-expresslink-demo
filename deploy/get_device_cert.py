from demo_badge import send_command, EXPRESSLINK_TX, EXPRESSLINK_RX
import busio
import time
uart = busio.UART(EXPRESSLINK_TX, EXPRESSLINK_RX, baudrate=115200, receiver_buffer_size=4096, timeout=0.1)
send_command(uart, "AT+CONF? Certificate pem")
time.sleep(3)
cert = uart.read()
print(cert.decode())
send_command(uart, "AT+CONF? ThingName")