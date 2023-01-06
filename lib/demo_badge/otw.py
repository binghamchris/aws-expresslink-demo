# from https://github.com/espressif/esp-aws-expresslink-eval/blob/2d620248e8bdb425aad14d0b69311b765445d46f/tools/otw.py#L24
# check for latest version https://github.com/espressif/esp-aws-expresslink-eval
# tested version upgrade from "ExpressLink V0.06.00 REFERENCE" -> "1.0.20"
# tested version upgrade from "1.0.20" -> "1.0.40"

# see OTW command definition, but Espressif ESP32-C3-MINI-1-A is similar, but not identical, protocol.
# https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-ota-updates.html#elpg-otw-firmware-update

import os
import time


def wait_for_ok_complete(uart):
    data = uart.readline();
    if data and data.decode().strip() == "OK COMPLETE":
        return "OK"
    elif not data:
        print("Timeout reading over serial")
    return "ERR"

def wait_for_ok(uart):
    data = uart.readline();
    if data and data.decode().strip() == "OK":
        return "OK"
    elif not data:
        print("Timeout reading over serial")
    return "ERR"

def cmd(uart, s):
    print(s)
    uart.write(s.encode() + "\n")

def otw(uart, file, new_version="unknown", blocksize=4096):
    new_version = new_version.strip().lower()
    print(f"Starting OTW for file {file} to new version {new_version} with blocksize {blocksize}.")

    try:
        if os.stat(file)[6] == 0:
            raise OSError()
    except OSError:
        print(f"OTW file {file} not found or has 0 bytes.")
        return

    uart.timeout = 10

    cmd(uart, "AT+CONF? Version")
    data = uart.readline().decode()
    if not data:
        print("Timeout reading over serial");
        return False

    if not data.startswith("OK"):
        print("Failure to get existing version")
        return False
    data = data[3:].strip().lower() # strip off "OK " prefix
    if data == new_version:
        print(f"Version {new_version} already on module. Skipping upgrade.")
        return True
    else:
        print(f"Current version on module: {data}")

    prerelease = "V0.06.00" in data.strip()
    if prerelease:
        print("Detected prerelease version, taking special care during upgrade.")

    filesize = os.stat(file)[6]
    cmd(uart, f"AT+OTW {filesize},{blocksize}")
    data = uart.readline()
    if not data:
        print("Timeout reading over serial");
        return False
    print(data)

    with open(file, 'rb') as stream:
        total_data_written = 0;

        if prerelease:
            ret = wait_for_ok(uart)
            if ret != "OK":
                print("\nError in OTW update")
                return False

        while True:
            data = stream.read(blocksize);
            if not data:
                break
            uart.write(data)
            total_data_written += len(data)
            ret = wait_for_ok(uart)
            print(f"Uploaded {total_data_written/filesize:.1%}")
            if ret != "OK":
                print("Error in OTW update")
                return False

    ret = wait_for_ok_complete(uart)

    time.sleep(5)

    cmd(uart, "AT+RESET")
    print(uart.readline())

    time.sleep(7)

    cmd(uart, "AT+CONF? About")
    print(uart.readline())

    cmd(uart, "AT+CONF? Version")
    print(uart.readline())

    print("OTW completed.")

    return True
