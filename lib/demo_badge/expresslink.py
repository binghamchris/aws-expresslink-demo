try:
    from typing import Optional, Tuple, Union # pylint: disable=unused-import
except ImportError:
    pass

import time
import re
import digitalio
from collections import namedtuple
from adafruit_debouncer import Debouncer


def readline(uart, debug=False, delay=True) -> str:
    if delay:
        time.sleep(0.1) # give it a bit of time to accumulate data - it might crash or loose bytes without it!

    l = b""
    counter = 300 # or ExpressLink.TIMEOUT
    for _ in range(counter):
        p = uart.readline()
        if p:
            l += p
        if l.endswith("\n"):
            break
    else:
        print("Expresslink uart timeout - response might be incomplete.")

    l = l.decode().strip("\r\n\x00\xff\xfe\xfd\xfc\xfb\xfa")
    if debug:
        print("< " + l)
    return l


class Event:
    MSG = 1 # parameter = topic index. A message was received on topic #.
    STARTUP = 2 # parameter = 0. The module has entered the active state.
    CONLOST = 3 # parameter = 0. Connection unexpectedly lost.
    OVERRUN = 4 # parameter = 0. Receive buffer Overrun (topic in detail).
    OTA = 5 # parameter = 0. OTA event (see OTA? command for details).
    CONNECT = 6 # parameter = Connection Hint. Connection established or failed.
    CONFMODE = 7 # parameter = 0. CONFMODE exit with success.
    SUBACK = 8 # parameter = Topic Index. Subscription accepted.
    SUBNACK = 9 # parameter = Topic Index. Subscription rejected.
    # 10..19 RESERVED
    SHADOW_INIT = 20 # parameter = Shadow Index. Shadow initialization successfully.
    SHADOW_INIT_FAILED = 21 # parameter = Shadow Index. Shadow initialization failed.
    SHADOW_DOC = 22 # parameter = Shadow Index. Shadow document received.
    SHADOW_UPDATE = 23 # parameter = Shadow Index. Shadow update result received.
    SHADOW_DELTA = 24 # parameter = Shadow Index. Shadow delta update received.
    SHADOW_DELETE = 25 # parameter = Shadow Index. Shadow delete result received
    SHADOW_SUBACK = 26 # parameter = Shadow Index. Shadow delta subscription accepted.
    SHADOW_SUBNACK = 27 # parameter = Shadow Index. Shadow delta subscription rejected.
    # <= 999 RESERVED


# https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-ota-updates.html#elpg-ota-commands
class OTACodes:
    NoOTAInProgress = 0 # No OTA in progress.
    UpdateProposed = 1 # A new module OTA update is being proposed. The host can inspect the version number and decide to accept or reject it. The {detail} field provides the version information (string).
    HostUpdateProposed = 2 # A new Host OTA update is being proposed. The host can inspect the version details and decide to accept or reject it. The {detail} field provides the metadata that is entered by the operator (string).
    OTAInProgress = 3 # OTA in progress. The download and signature verification steps have not been completed yet.
    NewExpressLinkImageReady = 4 # A new module firmware image has arrived. The signature has been verified and the ExpressLink module is ready to reboot. (Also, an event was generated.)
    NewHostImageReady = 5 # A new host image has arrived. The signature has been verified and the ExpressLink module is ready to read its contents to the host. The size of the file is indicated in the response detail. (Also, an event was generated.)


class Config:
    def __init__(self, el) -> None:
        self.el = el

    def _extract_value(self, query):
        success, line, error_code = self.el.cmd(f"CONF? {query}")
        if success:
            return line
        else:
            raise RuntimeError(f"failed to get config {query}: ERR{error_code} {line}")

    def _set_value(self, key, value):
        # escaping https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-commands.html#elpg-delimiters
        # use r"" raw strings if needed as input
        value.replace("\\", "\\\\")
        value.replace("\r", "\D")
        value.replace("\n", "\A")

        success, line, error_code = self.el.cmd(f"CONF {key}={value}")
        if success:
            return line
        else:
            raise RuntimeError(f"failed to set config {key}={value}: ERR{error_code} {line}")

    @property
    def About(self) -> str:
        return self._extract_value("About")

    @property
    def Version(self) -> str:
        return self._extract_value("Version")

    @property
    def TechSpec(self) -> str:
        return self._extract_value("TechSpec")

    @property
    def ThingName(self) -> str:
        return self._extract_value("ThingName")

    @property
    def Certificate(self) -> str:
        return self._extract_value("Certificate pem").lstrip("pem").strip()

    @property
    def CustomName(self) -> str:
        return self._extract_value("CustomName")

    @CustomName.setter
    def CustomName(self, value: str) -> str:
        return self._set_value("CustomName", value)

    @property
    def Endpoint(self) -> str:
        return self._extract_value("Endpoint")

    @Endpoint.setter
    def Endpoint(self, value: str):
        return self._set_value("Endpoint", value)

    @property
    def RootCA(self) -> str:
        return self._extract_value("RootCA pem").lstrip("pem").strip()

    @RootCA.setter
    def RootCA(self, value: str):
        return self._set_value("RootCA", value)

    @property
    def ShadowToken(self) -> str:
        return self._extract_value("ShadowToken")

    @ShadowToken.setter
    def ShadowToken(self, value: str):
        return self._set_value("ShadowToken", value)

    @property
    def DefenderPeriod(self) -> int:
        return int(self._extract_value("DefenderPeriod"))

    @DefenderPeriod.setter
    def DefenderPeriod(self, value: int):
        return self._set_value("DefenderPeriod", str(value))

    @property
    def HOTAcertificate(self) -> str:
        return self._extract_value("HOTAcertificate pem").lstrip("pem").strip()

    @HOTAcertificate.setter
    def HOTAcertificate(self, value: str):
        return self._set_value("HOTAcertificate", value)

    @property
    def OTAcertificate(self) -> str:
        return self._extract_value("OTAcertificate pem").lstrip("pem").strip()

    @OTAcertificate.setter
    def OTAcertificate(self, value: str):
        return self._set_value("OTAcertificate", value)

    @property
    def SSID(self) -> str:
        return self._extract_value("SSID")

    @SSID.setter
    def SSID(self, value: str):
        return self._set_value("SSID", value)

    @property
    def Passphrase(self):
        raise RuntimeError("write-only persistent key")

    @Passphrase.setter
    def Passphrase(self, value: str):
        return self._set_value("Passphrase", value)

    @property
    def APN(self) -> str:
        return self._extract_value("APN")

    @APN.setter
    def APN(self, value: str):
        return self._set_value("APN", value)

    @property
    def QoS(self) -> int:
        return self._extract_value("QoS")

    @QoS.setter
    def QoS(self, value: int):
        return self._set_value("QoS", str(value))

    def get_topic(self, topic_index):
        return self._extract_value(f"Topic{topic_index}")

    def set_topic(self, topic_index, topic_name):
        return self.el.cmd(f"CONF Topic{topic_index}={topic_name}")

    @property
    def enable_shadow(self) -> bool:
        return bool(self._extract_value("EnableShadow"))

    @enable_shadow.setter
    def enable_shadow(self, value: Union[bool, int]):
        return self._set_value("EnableShadow", "1" if bool(value) else "0") # accept bool as well as int as input

    def get_shadow(self, shadow_index):
        return self._extract_value(f"Shadow{shadow_index}")

    def set_shadow(self, shadow_index, shadow_name):
        return self.el.cmd(f"CONF Shadow{shadow_index}={shadow_name}")


class ExpressLink:
    """
    The default UART configuration shall be 115200, 8, N, 1 (baud rate: 115200; data bits: 8; parity: none; stop bits: 1).
    There is no hardware or software flow control for UART communications.
    """
    BAUDRATE = 115200

    """
    3.6.2 Response timeout
    The maximum runtime for every command must be listed in the datasheet.
    No command can take more than 120 seconds to complete (the maximum time for a TCP connection timeout).
    """
    TIMEOUT = 100 # CircuitPython has a maxium of 100 seconds.

    def __init__(self, uart, event_pin=None, wake_pin=None, reset_pin=None, default_uart_config=True, debug=True) -> None:
        print("ExpressLink initializing...")

        self.uart = uart
        self.config = Config(self)
        self.debug = debug
        self._topics = {}

        if default_uart_config:
            self.uart.baudrate = self.BAUDRATE
            self.uart.timeout = 0.1 # handle actual timeout in readline

        # When asserted, the ExpressLink module indicates to the host processor that
        # an event has occurred (disconnect error or message received on a subscribed
        # topic) and a notification is available in the event queue waiting to be
        # delivered. It is de-asserted when the event queue is emptied. A host processor
        # can connect an interrupt input to this signal (rising edge) or can poll the
        # event queue at regular intervals.
        if event_pin:
            self.event_signal = digitalio.DigitalInOut(event_pin)
            self.event_signal.direction = digitalio.Direction.INPUT
            self.event_signal.pull = digitalio.Pull.UP
            self.event_signal = Debouncer(self.event_signal, interval=0.001) # to get a usful rose/fell flag
        else:
            self.event_signal = None

        # When not asserted (high), the ExpressLink module is allowed to enter a low
        # power sleep mode. If in low power sleep mode and asserted (low), this will
        # awake the ExpressLink module.
        if wake_pin:
            self.wake_signal = digitalio.DigitalInOut(wake_pin)
            self.wake_signal.direction = digitalio.Direction.OUTPUT
            self.wake_signal.value = True
        else:
            self.wake_signal = None

        if reset_pin:
            self.reset_signal = digitalio.DigitalInOut(reset_pin)
            self.reset_signal.direction = digitalio.Direction.OUTPUT
            self.reset_signal.value = False
            time.sleep(1.00)
            self.reset_signal.value = True
            time.sleep(2.00)
        else:
            self.reset_signal = None

        if not self.self_test():
            print("ERROR: Failed ExpressLink UART self-test check!")
            self.ready = False
        else:
            self.ready = True

        print("ExpressLink ready!")

    def self_test(self):
        for _ in range(5):
            try:
                if self.debug:
                    print("ExpressLink: performing self-test...")
                self.uart.write(b"AT\n")
                r = readline(self.uart, self.debug)
                if r.strip() == "OK":
                    if self.debug:
                        print("ExpressLink UART self-test successful.")
                    return True
            except Exception as e:
                if self.debug:
                    print("ExpressLink self-test error:", e)
        return False

    def cmd(self, s: str) -> Tuple[bool, str, Optional[int]]:
        assert s

        # clear any previous un-read input data
        self.uart.reset_input_buffer()

        # see command format definition
        # https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-commands.html#elpg-commands-format
        self.uart.write(f"AT+{s}\r\n".encode())
        if self.debug:
            print("> AT+" + s)

        # see command response format definition
        # https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-commands.html#elpg-responses-formats
        l = readline(self.uart, self.debug)

        success = False
        additional_lines = 0
        error_code = None
        if l.startswith("OK"):
            success = True
            l = l[2:] # consume the OK prefix

            # optional numerical suffix [#] indicates the number of additional output lines,
            # with no additional lines expected if this suffix is omitted.
            r = l.find(" ")
            if r > 0:
                additional_lines = int(l[0:r])
                l = l[r:]
        elif l.startswith("ERR"):
            l = l[3:] # consume the ERR prefix
            r = l.find(" ")
            if r > 0:
                # https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-commands.html#elpg-table1
                error_code = int(l[0:r])
                l = l[r:]
            else:
                print(f"failed to parse error code: {len(l)} | {l}")
                return False, l, 2
        else:
            print(f"unexpected response: {len(l)} | {l}")
            return False, l, 2

        # read as many additional lines as needed, and concatenate them
        for _ in range(additional_lines):
            al = readline(self.uart, debug=False, delay=False)
            if not al:
                break
            l += "\n" + al

        return success, l.strip(), error_code

    def info(self):
        # see configuration dictionary
        # https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-configuration-dictionary.html
        print(self.config.About)
        print(self.config.Version)
        print(self.config.TechSpec)
        print(self.config.ThingName)
        print(self.config.CustomName)
        print(self.config.Endpoint)
        print(self.config.SSID)
        print(self.config.Certificate)
        self.cmd("TIME?")
        self.cmd("WHERE?")
        self.cmd("CONNECT?")

    def connect(self, non_blocking=False):
        x = "!" if non_blocking else ""
        if not non_blocking:
            print("ExpressLink connecting to the AWS Cloud... (might take a few seconds)")
        return self.cmd(f"CONNECT{x}")

    def disconnect(self):
        return self.cmd("DISCONNECT")

    def sleep(self, duration, mode=None):
        if not mode:
            return self.cmd(f"SLEEP {duration}")
        else:
            return self.cmd(f"SLEEP{mode} {duration}")

    def reset(self):
        if self.reset_signal:
            self.reset_signal.value = False
            time.sleep(1.00)
            self.reset_signal.value = True
            time.sleep(2.00)
        # double reset is twice as good (AT commands might be stuck, so hardware reset + software reset)
        return self.cmd("RESET")

    def factory_reset(self):
        return self.cmd("FACTORY_RESET")

    def confmode(self, params=None):
        # https://github.com/espressif/esp-aws-expresslink-eval#611-using-confmode
        if params:
            return self.cmd(f"CONFMODE {params}")
        else:
            return self.cmd("CONFMODE AWS-ExpressLink-Demo-Badge")

    @property
    def connected(self) -> Tuple[bool, bool]:
        success, line, err = self.cmd("CONNECT?")
        if not success:
            raise ValueError(f"CONNECT? {err} {line}")
        r = line.split(" ")
        is_connected = False
        if r[0] == "1":
            is_connected = True
        is_customer_account = False
        if r[1] == "1":
            is_customer_account = True
        return is_connected, is_customer_account

    @property
    def time(self):
        success, line, _ = self.cmd("TIME?")
        if not success or not line.startswith("date"):
            return None

        # {date YYYY/MM/DD} {time hh:mm:ss.xx} {source}
        # date 2022/10/30 time 09:38:34.04 SNTP
        dt = namedtuple("datetime", ("year", "month", "day", "hour", "minute", "second", "microsecond", "source"))
        return dt(
            year=int(line[5:9]),
            month=int(line[10:12]),
            day=int(line[13:15]),
            hour=int(line[21:23]),
            minute=int(line[24:26]),
            second=int(line[27:29]),
            microsecond=int(line[30:32]) * 10**4,
            source=line[33:]
        )

    @property
    def where(self):
        success, line, _ = self.cmd("WHERE?")
        if not success or not line.startswith("date"):
            return None
        # {date} {time} {lat} {long} {elev} {accuracy} {source}
        return line

    @property
    def ota_state(self):
        _, line, _ = self.cmd("OTA?")
        r = line.split(" ", 1)
        code = int(r[0])
        detail = None # detail is optional
        if len(r) == 2:
            detail = r[1]
        return code, detail

    def ota_accept(self):
        return self.cmd("OTA ACCEPT")

    def ota_read(self, count: int):
        return self.cmd(f"OTA READ {count}")

    def ota_seek(self, address: Optional[int]=None):
        if address:
            return self.cmd(f"OTA SEEK {address}")
        else:
            return self.cmd(f"OTA SEEK")

    def ota_close(self):
        return self.cmd("OTA CLOSE")

    def ota_flush(self):
        return self.cmd("OTA FLUSH")

    def get_event(self):
        # OK [{event_identifier} {parameter} {mnemonic [detail]}]{EOL}
        success, line, _ = self.cmd("EVENT?")
        if (success and not line) or not success:
            return None, None, None, None

        if self.event_signal: # update signal state after getting an event and debounce signal
            self.event_signal.update()
            self.event_signal.update()
            self.event_signal.update()

        # https://docs.aws.amazon.com/iot-expresslink/latest/programmersguide/elpg-event-handling.html
        event_id, parameter, mnemonic, detail = re.match("(\d+) (\d+) (\S+)( \S+)?", line).groups()
        return int(event_id), int(parameter), mnemonic, detail

    def wait_for_event(self, polling=None):
        if polling:
            while True:
                event_id, parameter, mnemonic, detail = self.get_event()
                if event_id:
                    return event_id, parameter, mnemonic, detail
                time.sleep(polling)
        else:
            while True:
                if self.event_signal:
                    self.event_signal.update()
                    if self.event_signal.value == True:
                        return
                else:
                    print("ExpressLink: event signal pin not defined.")
                    return None, None, None, None

    @property
    def topics(self):
        return self._topics.copy()

    def subscribe(self, topic_index, topic_name):
        topic_name = topic_name.strip()
        self._topics[topic_index] = topic_name
        self.config.set_topic(topic_index, topic_name)
        return self.cmd(f"SUBSCRIBE{topic_index}")

    def unsubscribe(self, *, topic_name=None, topic_index=None):
        if topic_name:
            topic_index = self._topics.values().index(topic_name)
        if topic_index:
            del self._topics[topic_index]
        return self.cmd(f"UNSUBSCRIBE{topic_index}")

    def get_message(self, topic_index=None, topic_name=None):
        if topic_name:
            topic_index = self._topics.values().index(topic_name)
        elif topic_index and topic_index > 0:
            topic_name = self._topics[topic_index]
        elif topic_index is None:
            topic_index = ''

        success, line, error_code = self.cmd(f"GET{topic_index}")
        if topic_index == '' or topic_index == 0:
            # next message pending or unassigned topic
            if success and line:
                topic_name, message = line.split("\n", 1)
                return topic_name, message
            else:
                return True, None
        else:
            # indicated topic with index
            if success:
                return topic_name, line
            else:
                return False, error_code

    def publish(self, topic_index: int, message: str):
        return self.cmd(f"SEND{topic_index} {message}")

    def shadow_init(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} INIT")

    def shadow_doc(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} DOC")

    def shadow_get_doc(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} GET DOC")

    def shadow_update(self, new_state: str, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} UPDATE {new_state}")

    def shadow_get_update(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} GET UPDATE")

    def shadow_subscribe(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} SUBSCRIBE")

    def shadow_unsubscribe(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} UNSUBSCRIBE")

    def shadow_get_delta(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} GET DELTA")

    def shadow_delete(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} DELETE")

    def shadow_get_delete(self, index: Union[int, str]=''):
        return self.cmd(f"SHADOW{index} GET DELETE")
