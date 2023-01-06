import binascii
import digitalio
from adafruit_debouncer import Debouncer

from .ndef_encoder import encode_uri, encode_vcard

class NT3Hxxxx:
    def __init__(self, device, field_detect_pin) -> None:
        self.device = device

        # FD_ON register might need to be set first, see Section 8.4, https://www.nxp.com/docs/en/data-sheet/NT3H2111_2211.pdf
        field_detect = digitalio.DigitalInOut(field_detect_pin)
        field_detect.direction = digitalio.Direction.INPUT
        self.field_detect = Debouncer(field_detect)
        # ExpressLinkBadge2022 contains external 10k pull-up for NFC_FIELD_DETECT

    def info(self):
        d = self.read_page(0)
        print(f"Addr: {d[0]}")
        print(f"UID:  {binascii.hexlify(d[1:7])}")
        print(f"Internal: {binascii.hexlify(d[7:10])}")
        print(f"Static lock byte: {binascii.hexlify(d[10:12])}")
        print(f"Capability Container: {binascii.hexlify(d[12:])}")

        # show first couple of user memory pages
        print(self.read_page(1))
        print(self.read_page(2))
        print(self.read_page(3))

    def read_page(self, page):
        register = bytearray(1)
        register[0] = page
        data = bytearray(16) # each page contains 16 bytes
        with self.device:
            self.device.write_then_readinto(register, data)
        return data

    def read_register(self, rega):
        register = bytearray(2)
        register[0] = 0xFE
        register[1] = rega
        data = bytearray(1)
        with self.device:
            self.device.write_then_readinto(register, data)
        return data[0]

    def write_register(self, rega, mask, regdat):
        data = bytearray(4)
        data[0] = 0xFE
        data[1] = rega
        data[2] = mask
        data[3] = regdat
        with self.device:
            self.device.write(data)

    def write_page(self, page_id, data):
        # pad with 0x00 to a full 16-byte page
        if len(data) < 16:
            data += bytearray(b"\x00"*(16-len(data)))
        assert len(data) == 16

        msg = bytearray([page_id]) + data
        print(f"NFC NT3Hxxxx: writing to page {page_id}:", msg[1:])
        with self.device:
            self.device.write(msg)

    def write_user_eeprom(self, raw):
        if len(raw) >= 880:
            raise ValueError(f"NFC NT3Hxxxx: not enough space for {len(raw)} bytes")

        page_id = 1
        for i in range(0, len(raw), 16):
            data = bytearray(raw[i:i+16])
            self.write_page(page_id, data)
            page_id += 1

    def provision(self, size='1k'):
        # This function only needs to be called once to provision a fresh-from-factory Demo Badge.
        self._provision_capability_container(size)
        self._provision_default_url()

    def _provision_capability_container(self, size):
        # based on the available eeprom size:
        # 1k model=0x6D
        # 2k model=0xEA
        # https://github.com/mofosyne/NXP_NTAG_I2C_Demo_Annotated/blob/b5cef1f39811b4bccb3e27ce226bec0d99bea969/NTAG_I2C_Demo_AndroidApp/src/com/nxp/nfc_demo/reader/Ntag_I2C_Commands.java#L1168
        magic = {
            '1k': 0x6D,
            '2k': 0xEA,
        }

        data = self.read_page(0)

        if data[12:16] == bytearray([0xE1, 0x10, 0x6D, 0x00]):
            print("NFC NT3Hxxxx already provisioned for 1k size.")
            if size == '1k':
                return
            # continue to re-provision with new size
        elif data[12:16] == bytearray([0xE1, 0x10, 0xEA, 0x00]):
            print("NFC NT3Hxxxx already provisioned for 2k size.")
            if size == '2k':
                return
            # continue to re-provision with new size
        else:
            print("NFC NT3Hxxxx not provisioned yet.")

        # I2C slave address is stored in most significant 7 bits of byte 0 in block 0.
        # However, when reading block 0, NTAG I2C plus always returns 04h for byte 0.
        data[0] = 0x55<<1 # Default address 0x55, but stored in the MSBs: 0x55<<1=0xAA

        # NDEF format specification in CC
        data[12] = 0xE1
        data[13] = 0x10
        data[14] = magic[size]
        data[15] = 0x00

        self.write_page(0, data)
        print(f"NFC NT3Hxxxx provisioned for size {size}.")

    def _provision_empty_ndef_message(self):
        # 0x03 as NDEF Message
        # 0x00 zero following bytes
        # 0xFE TVL Terminator
        empty_ndef_message =  b'\x03\x00\xfe'
        d = self.read_page(1)
        if d[:3] != empty_ndef_message:
            self.write_page(1, empty_ndef_message)
            print("NFC NT3Hxxxx successfully written empty NDEF message.")
        else:
            print("NFC NT3Hxxxx already contains empty NDEF message.")

    def _provision_default_url(self):
        default_url = "https://aws.amazon.com/iot-expresslink/"
        data = self.read_page(1) + self.read_page(2) + self.read_page(3)
        r = encode_uri(default_url)
        if data[:len(r)] != r:
            print("NFC NT3Hxxxx successfully written default URL.")
            self.set_url(default_url)
        else:
            print("NFC NT3Hxxxx already contains default URL.")

    def set_url(self, url: str="https://aws.amazon.com/iot-expresslink/"):
        r = encode_uri(url)
        self.write_user_eeprom(r)

    def set_vcard(self, **kwargs):
        r = encode_vcard(**kwargs)
        self.write_user_eeprom(r)
