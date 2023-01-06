import microcontroller
import binascii
import time
import displayio
import terminalio
import supervisor
import usb_cdc

import adafruit_imageload
from adafruit_ticks import ticks_add, ticks_less, ticks_ms
from adafruit_display_text import label
from adafruit_led_animation.animation.rainbowcomet import RainbowComet

from .badge import Badge
from .expresslink import Event
from .otw import otw
from .qrcode import encode_qr_code


def render_aws_logo():
    bitmap, palette = adafruit_imageload.load(
        "/lib/demo_badge/pictures/aws_logo.bmp",
        bitmap=displayio.Bitmap,
        palette=displayio.Palette
    )
    tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
    group = displayio.Group()
    group.append(tile_grid)
    return group


def provision(badge: Badge):
    peripherals_missing = (
        not badge.accelerometer or
        not badge.temperature_humidity or
        not badge.nfc_tag or
        (badge.ambient_light.value < 10 or badge.ambient_light.value > 30000)
    )
    if peripherals_missing:
        return False

    for _ in range(3):
        try:
            badge.nfc_tag.provision()
            break
        except Exception as e:
            print(e)
            time.sleep(1)

    if badge.expresslink.ready:
        # ExpressLink fimware upgrade over-the-wire
        otw(uart=badge.expresslink.uart, file="/lib/demo_badge/v2.4.1.bin", new_version="2.4.1")

    return True


def create_test_screen():
    splash = displayio.Group()

    color_bitmap = displayio.Bitmap(240, 240, 1)
    color_palette = displayio.Palette(1)
    color_palette[0] = 0x00FF00  # Bright Green

    bg_sprite = displayio.TileGrid(color_bitmap, pixel_shader=color_palette, x=0, y=0)
    splash.append(bg_sprite)

    inner_bitmap = displayio.Bitmap(230, 230, 1)
    inner_palette = displayio.Palette(1)
    inner_palette[0] = 0xAA0088  # Purple
    inner_sprite = displayio.TileGrid(inner_bitmap, pixel_shader=inner_palette, x=5, y=5)
    splash.append(inner_sprite)

    text_group = displayio.Group(scale=1, x=10, y=20)
    data_label = label.Label(terminalio.FONT, text="", color=0xffffff)
    text_group.append(data_label)
    splash.append(text_group)

    return splash, data_label


def update_self_test_report(badge, data_label, bundle_version, firmware_check, button1_pressed, button2_pressed, button3_pressed, ambient_light_samples, expresslink_event_signal):
    avg_light = sum(ambient_light_samples)/len(ambient_light_samples)
    ambiant_light_ok = "OK" if avg_light > 10 and avg_light < 30000 else "UNEXPTECTED"

    if badge.temperature_humidity:
        temperature = badge.temperature_humidity.temperature
        relative_humidity = badge.temperature_humidity.relative_humidity
        temperature_humidity = f"OK | {temperature:.1f} C | {relative_humidity:.0f}%"
    else:
        temperature_humidity = "FAILED"

    if badge.accelerometer:
        x, y, z = badge.accelerometer.acceleration
        accelerometer = f"OK | {x:+3.1f} {y:+3.1f} {z:+3.1f}"
    else:
        x, y, z = 0.0, 0.0, 0.0
        accelerometer = "FAILED"

    if badge.nfc_tag:
        nfc_id = "OK | ID:" + binascii.hexlify(badge.nfc_tag.read_page(0)[:7]).decode()
    else:
        nfc_id = "FAILED"

    if badge.expresslink.self_test():
        expresslink_check = f"OK | {badge.expresslink.config.Version}"
    else:
        expresslink_check = "FAIL"

    if expresslink_event_signal:
        expresslink_event_check = "OK"
    else:
        expresslink_event_check = "FAIL"

    data_label.text = "\n".join([
        "Self-Test Results:",
        f"{bundle_version} | Bundle",
        f"{firmware_check}",
        f"{expresslink_check} | ExpressLink Firmware",
        f"{expresslink_event_check} | ExpressLink EVENT",
        f"{ambiant_light_ok} | {avg_light:4.0f} | Ambient Light",
        f"{accelerometer} | LIS3DH",
        f"{temperature_humidity} | SHT-30",
        f"{nfc_id} | NFC NT3H",
        f"{'OK' if button1_pressed else 'not yet'} | Button 1",
        f"{'OK' if button2_pressed else 'not yet'} | Button 2",
        f"{'OK' if button3_pressed else 'not yet'} | Button 3",
    ])


def run():
    logo_group = render_aws_logo()
    badge = Badge(display_init_screen=logo_group)

    if not provision(badge):
        print("Provisioning failed!")
        print("Please inform a workstop staff member to get a replacement Demo Badge.")
        while True:
            pass

    # disable auto-reload after provisioning,
    # to prevent spurious USB filesystem events causing unexpected reboots for workshop participants
    supervisor.disable_autoreload()

    badge.back_led.blink = True

    badge.led_animation = RainbowComet(badge.leds, speed=0.1)
    badge.leds.brightness = 0.1

    qr_group = encode_qr_code(badge.display, "https://aws.amazon.com/iot-expresslink/", qr_type=3)
    test_group, data_label = create_test_screen()

    ambient_light_samples = []
    button1_pressed = False
    button2_pressed = False
    button3_pressed = False

    expresslink_event_signal_check_state = 0
    expresslink_event_signal = False

    bundle_version = "unknown"
    try:
        with open("VERSION.txt") as boot:
            bundle_version = boot.read().strip()

        data_label.text = '\n'.join(["Bundle", "Version"] + bundle_version.split('T'))
        data_label.scale = 3
        data_label.anchor_point = (0.5, 0.5)
        data_label.anchored_position = (120, 120)
        badge.display.show(test_group)
        time.sleep(5)
        data_label.text = ""
        data_label.scale = 1
        data_label.anchor_point = (0, 0)
        data_label.anchored_position = (0, 0)
    except:
        pass

    circuit_python, board_name = "unknown", "unknown"
    try:
        with open("boot_out.txt") as boot:
            lines = boot.read().split("\n")
            circuit_python = lines[0].split(";", 1)[0][23:28]
            board_name = lines[1].split(":", 1)[1].strip()
    except:
        time.sleep(5) # finish all write operations
        microcontroller.reset()
        while True: pass

    if circuit_python == "7.3.3" and board_name == "raspberry_pi_pico":
        firmware_check = f"OK | {circuit_python} | {board_name}"
    else:
        firmware_check = f"FAIL | {circuit_python} | {board_name}"

    badge.expresslink.debug = False

    ################################################################################

    next_display_update = ticks_ms()
    next_data_update = ticks_ms()

    while True:
        badge.update()

        time.sleep(0.1)
        if ticks_less(next_display_update, ticks_ms()):
            # Ctrl-C might not be recognized if the input buffer is in a weird state.
            # https://github.com/mu-editor/mu/issues/842
            # https://forums.adafruit.com/viewtopic.php?f=60&t=151826
            # https://github.com/micropython/micropython/issues/7867
            # https://github.com/micropython/micropython/issues/7996
            # https://github.com/micropython/micropython/commit/587339022689187a1acbccc1d0e2425a67385ff7
            usb_cdc.console.reset_input_buffer()
            usb_cdc.console.reset_output_buffer()
            usb_cdc.console.flush()

            print("\n\n\nWelcome to the AWS IoT ExpressLink Demo Badge.")
            print("You successfully connected to the serial interface.")
            print("Press Ctrl-C to interrupt this loop!")
            if badge.display.root_group == logo_group:
                badge.display.show(qr_group)
            elif badge.display.root_group == qr_group:
                badge.display.show(test_group)
            else:
                badge.display.show(logo_group)

            next_display_update = ticks_add(ticks_ms(), 5000)

        if not badge.button1.value:
            button1_pressed = True
        if not badge.button2.value:
            button2_pressed = True
        if not badge.button3.value:
            button3_pressed = True

        if badge.button1.pressed or badge.button2.pressed or badge.button3.pressed:
            print(data_label.text)

        # moving average filter
        # raw values in range 0 to 65535
        ambient_light_samples.append(badge.ambient_light.value)
        if len(ambient_light_samples) > 10:
            ambient_light_samples = ambient_light_samples[1:]

        if expresslink_event_signal_check_state == 0:
            if badge.expresslink.event_signal.value:
                # there must be at least one pending event
                expresslink_event_signal_check_state += 1
        elif expresslink_event_signal_check_state == 1:
            event_id, _, _, _ = badge.expresslink.get_event()
            if event_id and event_id != Event.STARTUP:
                print("Unexpected event:", event_id)
            if not badge.expresslink.event_signal.value:
                # it must be LOW after consuming the STARTUP event
                expresslink_event_signal = True
                expresslink_event_signal_check_state = 99

        if ticks_less(next_data_update, ticks_ms()):
            update_self_test_report(badge, data_label, bundle_version, firmware_check, button1_pressed, button2_pressed, button3_pressed, ambient_light_samples, expresslink_event_signal)
            next_data_update = ticks_add(ticks_ms(), 1000)
