from demo_badge import Badge
from demo_badge.expresslink import Event, OTACodes

badge = Badge()

# Connect to AWS, stop if there is any error
success, status, err = badge.expresslink.connect()
if not success:
    print(f"Unable to connect: {err} {status}")
    while True: pass

url_to_share = "https://cloudypandas.ch"

print(f"URL to share is: {url_to_share}")

print("Setting NFC tag...")
badge.nfc_tag.set_url(url_to_share)

print("Displaying QR code...")
badge.show_qr_code(url_to_share)

while True:
    badge.update()