"""
https://learn.adafruit.com/adafruit-pn532-rfid-nfc/ndef
https://www.oreilly.com/library/view/beginning-nfc/9781449324094/ch04.html

TLV: Tag Field, Length Field, Value Field

0x03 Field Type for NDEF
     Length Field: one bytes 0x00-0xFF; or three bytes (0xFF + 0x00FF-0xFFFE)

0xFE TLV Terminator
"""

import struct

uri_prefixes = {
    # 0x00 = full uri
    0x01: "http://www.",
    0x02: "https://www.",
    0x03: "http://",
    0x04: "https://",
    0x05: "tel:",
    0x06: "mailto:",
    0x07: "ftp://anonymous:anonymous@",
    0x08: "ftp://ftp.",
    0x09: "ftps://",
    0x0A: "sftp://",
    0x0B: "smb://",
    0x0C: "nfs://",
    0x0D: "ftp://",
    0x0E: "dav://",
    0x0F: "news:",
    0x10: "telnet://",
    0x11: "imap:",
    0x12: "rtsp://",
    0x13: "urn:",
    0x14: "pop:",
    0x15: "sip:",
    0x16: "sips:",
    0x17: "tftp:",
    0x18: "btspp://",
    0x19: "btl2cap://",
    0x1A: "btgoep://",
    0x1B: "tcpobex://",
    0x1C: "irdaobex://",
    0x1D: "file://",
    0x1E: "urn:epc:id:",
    0x1F: "urn:epc:tag:",
    0x20: "urn:epc:pat:",
    0x21: "urn:epc:raw:",
    0x22: "urn:epc:",
    0x23: "urn:nfc:",
}

def encode_uri(uri: str):
    if len(uri) > 2000: # 2kB - headers
        raise ValueError(f"URI too long with {len(uri)}")

    encoded = b''
    for k, v in sorted(uri_prefixes.items()):
        if uri.startswith(v):
            encoded = struct.pack('>B', k) + uri[len(v):].encode('utf-8')
            break
    else:
        encoded = b'\x00' + uri.encode('utf-8')

    record_header, payload_length = encode_ndef_record_header(0x01, len(encoded)) # Well-Known Record

    record = b''.join([
        record_header,
        b'\x01', # Type Length for Record Type Indicator
        payload_length, # Payload Length, either 1 or 4 bytes
        b'\x55', # Record Type Indicator for URI
        encoded,
    ])
    return encode_ndef_message(record)

def encode_vcard(*, first_name: str, last_name: str, phone: str, email: str, full_name: str=None, vcard: str=None):
    if not full_name:
        full_name = f"{first_name} {last_name}"

    if vcard:
        encoded = vcard.encode('utf-8')
    else:
        encoded = f"""
BEGIN:VCARD
VERSION:3.0
N:{last_name};{first_name};;;
FN:{full_name}
TEL;TYPE=HOME,VOICE:{phone}
EMAIL;TYPE=PREF,INTERNET:{email}
END:VCARD
        """.strip().encode('utf-8')

    record_header, payload_length = encode_ndef_record_header(0x02, len(encoded)) # MIME Media Record

    mime = b"text/vCard"

    record = b''.join([
        record_header, # NDEF Record Header, Begin of message, End of message, Not chunked, Short record, Well Known Type
        struct.pack(">B", len(mime)), # Type Length for Record Type Indicator
        payload_length, # Payload Length, either 1 or 4 bytes
        mime,
        encoded,
    ])
    return encode_ndef_message(record)

def encode_ndef_record_header(typ, len):
    if len <= 255:
        record_header = 0xD0 # Begin of message, End of message, Not chunked, Short record
        payload_length = struct.pack('>B', len)
    else:
        record_header = 0xC0 # Begin of message, End of message, Not chunked, not Short record
        payload_length = struct.pack('>I', len) # 4-byte payload length
    record_header |= typ

    return bytes([record_header]), payload_length

def encode_ndef_record_length(l):
    if isinstance(l, list) or isinstance(l, bytes) or isinstance(l, bytearray) or isinstance(l, str):
        l = len(l)

    if l <= 0xFF:
        return struct.pack(">B", l)
    elif l > 0xFF and l <= 0xFFFE:
        return b'\xFF' + struct.pack(">H", l)
    else:
        raise ValueError("NDEF Record length invalid")

def encode_ndef_message(records):
    if not isinstance(records, list):
        records = [records]

    encoded = b'\x03' # NDEF Message
    for record in records:
        encoded += encode_ndef_record_length(record)
        encoded += record
    encoded += b'\xFE' # TLV Terminator
    return encoded
