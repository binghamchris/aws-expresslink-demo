from demo_badge import Badge
from demo_badge.expresslink import Event, OTACodes

badge = Badge()

def change_url(url_to_share):
    print(f"URL to share is: {url_to_share}")

    print("Setting NFC tag...")
    badge.nfc_tag.set_url(url_to_share)

    print("Displaying QR code...")
    badge.show_qr_code(url_to_share)

# Connect to AWS, stop if there is any error
success, status, err = badge.expresslink.connect()
if not success:
    print(f"Unable to connect: {err} {status}")
    while True: pass

change_url("https://cloudypandas.ch")

while True:
    badge.update()

    if badge.button1.pressed:
        change_url("https://cloudypandas.ch")
    if badge.button2.pressed:
        change_url("https://www.cloudreach.com/en/technical-blog/")
    if badge.button3.pressed:
        change_url("https://github.com/binghamchris")
    