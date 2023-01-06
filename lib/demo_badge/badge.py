import board
import busio
import digitalio
import displayio
import analogio
import usb_cdc
from adafruit_ticks import ticks_add, ticks_less, ticks_ms

import adafruit_miniqr
import adafruit_debouncer
import adafruit_lis3dh
import adafruit_sht31d
import neopixel
from adafruit_st7789 import ST7789
from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_debouncer import _DEBOUNCED_STATE ,_CHANGED_STATE

from .hardware import *
from .expresslink import ExpressLink
from .nfc_nt3hxxxx import NT3Hxxxx
from .qrcode import encode_qr_code
from .simple_led import SimpleLED


class Badge:
    def __init__(self, display_init_screen=None) -> None:
        print("Demo Badge initializing...")
        self._first_update = True

        self.display = self._init_display(display_init_screen)

        i2c = busio.I2C(I2C_SCL, I2C_SDA)

        try:
            self.accelerometer = adafruit_lis3dh.LIS3DH_I2C(i2c, address=LIS3DH_I2C_ADDR)
        except:
            self.accelerometer = None
            print("Error: Failed to init accelerometer device!")

        try:
            self.temperature_humidity = adafruit_sht31d.SHT31D(i2c, address=SHT30_I2C_ADDR)
        except:
            self.temperature_humidity = None
            print("Error: Failed to init temperature_humidity device!")

        try:
            self.nfc_tag = NT3Hxxxx(I2CDevice(i2c, NFC_I2C_ADDR), NFC_FIELD_DETECT)
            self.nfc_tag.write_register(1, 0xFF, 0x01) # set session register for LAST_NDEF_BLOCK to 0x01
        except:
            self.nfc_tag = None
            print("Error: Failed to init nfc_tag device!")
        self.nfc_tag_read = False
        self._next_nfc_tag_read = ticks_ms()

        self.ambient_light = analogio.AnalogIn(AMBIENT_LIGHT_ANALOG)

        # Waveshare RP2040-Plus connects VSYS via a 200k/100k voltage divider to GP29/ADC3
        self.battery_voltage = analogio.AnalogIn(board.VOLTAGE_MONITOR)

        self.leds = neopixel.NeoPixel(pin=NEOPIXEL_DATA, n=NEOPIXEL_CHAIN_LENGTH, brightness=0.2)
        self.led_animation = None

        self.back_led = SimpleLED(board.GP25)

        # The default UART configuration shall be 115200, 8, N, 1
        # (baud rate: 115200; data bits: 8; parity: none; stop bits: 1).
        # There is no hardware or software flow control for UART communications.
        # Buffer size to most likely to fit a certificate in PEM format.
        self._expresslink_uart = busio.UART(EXPRESSLINK_TX, EXPRESSLINK_RX, baudrate=ExpressLink.BAUDRATE, receiver_buffer_size=4096)
        self.expresslink = ExpressLink(self._expresslink_uart, event_pin=EXPRESSLINK_EVENT, wake_pin=EXPRESSLINK_WAKE, reset_pin=EXPRESSLINK_RESET)

        self._expresslink_debug_uart = None
        # self._expresslink_debug_uart = busio.UART(EXPRESSLINK_DEBUG_TX, EXPRESSLINK_DEBUG_RX, baudrate=115200, timeout=1, receiver_buffer_size=4096)

        def user_button(gpio):
            pin = digitalio.DigitalInOut(gpio)
            pin.direction = digitalio.Direction.INPUT
            pin.pull = digitalio.Pull.UP
            return adafruit_debouncer.Button(pin, long_duration_ms=5000)
        self.button1 = user_button(BUTTON1)
        self.button2 = user_button(BUTTON2)
        self.button3 = user_button(BUTTON3)

        print("Demo Badge ready!")

    def _init_display(self, display_init_screen=None):
        displayio.release_displays()
        if hasattr(self, "spi") and self.spi:
            self.spi.deinit()

        self.spi = busio.SPI(clock=DISPLAY_SPI_SCK, MOSI=DISPLAY_SPI_MOSI)
        while not self.spi.try_lock():
            pass
        self.spi.configure(baudrate=48 * 10**6) # MHz
        self.spi.unlock()

        display_bus = displayio.FourWire(self.spi, command=DISPLAY_DC, chip_select=DISPLAY_SPI_CS)
        display = ST7789(
            display_bus,
            width=240,
            height=240,
            rotation=180,
            rowstart=80, # ST7789 can drive 320px, but we only have 240px, so skip the first 80px.
            backlight_pin=DISPLAY_BACKLIGHT
        )
        display.brightness = 0.75 # 0.0=off, 1.0=full brightness

        if display_init_screen:
            display.show(display_init_screen)

        return display

    def update(self):
        self.button1.update()
        self.button2.update()
        self.button3.update()

        if self._expresslink_debug_uart and self._expresslink_debug_uart.in_waiting:
            print(self._expresslink_debug_uart.readline())

        if self.button3.long_press:
            # Ctrl-C might not be recognized if the input buffer is in a weird state.
            # https://github.com/mu-editor/mu/issues/842
            # https://forums.adafruit.com/viewtopic.php?f=60&t=151826
            # https://github.com/micropython/micropython/issues/7867
            # https://github.com/micropython/micropython/issues/7996
            # https://github.com/micropython/micropython/commit/587339022689187a1acbccc1d0e2425a67385ff7
            usb_cdc.console.reset_input_buffer()
            usb_cdc.console.reset_output_buffer()
            usb_cdc.console.flush()
            print("usb_cdc: flushed all buffers.")

        if self._first_update:
            self._first_update = False
            self.expresslink.event_signal._set_state(_DEBOUNCED_STATE | _CHANGED_STATE)
        else:
            self.expresslink.event_signal.update()

        # FD pin is only useful when used as interrupt - otherwise a short pulse might be missed
        self.nfc_tag.field_detect.update()

        # read NS_REG register and extract NDEF_DATA_READ at bit7
        if self.nfc_tag.read_register(6) & 0x80:
            if ticks_less(self._next_nfc_tag_read, ticks_ms()):
                # debounce the value if multiple reads occur within a short time, as is common on most smartphones
                self.nfc_tag_read = True
                self._next_nfc_tag_read = ticks_add(ticks_ms(), 500)
        else:
                self.nfc_tag_read = False

        if self.led_animation:
            self.led_animation.animate()

        self.back_led.update()

    def show_qr_code(self, data: str="https://aws.amazon.com/iot-expresslink/", qr_type=6, error_correct=adafruit_miniqr.L) -> displayio.Group:
        if not data.strip():
            self.display.show(None)
            return
        try:
            qr_group = encode_qr_code(self.display, data, qr_type, error_correct)
            self.display.show(qr_group)
            return qr_group
        except Exception as e:
            print(e)
            return displayio.Group()

    def show_picture(self, name, force_fail=False):
        if name == 'none':
            self.display.show(None)
            return
        try:
            import gc
            gc.collect()
            import adafruit_imageload # import only on-demand to save memory
            bitmap, palette = adafruit_imageload.load(
                f"/lib/demo_badge/pictures/{name}.bmp",
                bitmap=displayio.Bitmap,
                palette=displayio.Palette
            )
            tile_grid = displayio.TileGrid(bitmap, pixel_shader=palette)
            group = displayio.Group()
            group.append(tile_grid)
            self.display.show(group)
            gc.collect()
            return group
        except Exception as e:
            if force_fail:
                raise e
            print(e)
            import gc
            self.display.show(None)
            return self.show_picture(name, True)

    def set_led_animation(self, animation):
        # import each animation only on-demand to save memory

        if animation == 'Static':
            self.led_animation = None
            self.leds.brightness = 0.3
            self.leds.auto_write = True
        elif animation == 'Blink':
            from adafruit_led_animation.animation.blink import Blink
            self.led_animation = Blink(self.leds, speed=0.2, color=0xff9900)
        elif animation == 'SparklePulse':
            from adafruit_led_animation.animation.sparklepulse import SparklePulse
            self.led_animation = SparklePulse(self.leds, speed=0.1, color=0xff9900)
        elif animation == 'Comet':
            from adafruit_led_animation.animation.comet import Comet
            self.led_animation = Comet(self.leds, speed=0.2, color=0xff9900, tail_length=2)
            self.leds.brightness = 0.8
        elif animation == 'Chase':
            from adafruit_led_animation.animation.chase import Chase
            self.led_animation = Chase(self.leds, speed=0.1, color=0xff9900, size=1, spacing=2)
            self.leds.brightness = 0.2
        elif animation == 'Pulse':
            from adafruit_led_animation.animation.pulse import Pulse
            self.led_animation = Pulse(self.leds, speed=0.1, color=0xff9900)
        elif animation == 'Sparkle':
            from adafruit_led_animation.animation.sparkle import Sparkle
            self.led_animation = Sparkle(self.leds, speed=0.1, color=0xff9900)
        elif animation == 'RainbowChase':
            from adafruit_led_animation.animation.rainbowchase import RainbowChase
            self.led_animation = RainbowChase(self.leds, speed=0.1, size=5, spacing=0, step=16)
        elif animation == 'RainbowSparkle':
            from adafruit_led_animation.animation.rainbowsparkle import RainbowSparkle
            self.led_animation = RainbowSparkle(self.leds, speed=0.1)
        elif animation == 'RainbowComet':
            from adafruit_led_animation.animation.rainbowcomet import RainbowComet
            self.led_animation = RainbowComet(self.leds, speed=0.1)
        elif animation == 'ColorCycle':
            from adafruit_led_animation.animation.colorcycle import ColorCycle
            self.led_animation = ColorCycle(self.leds, speed=0.05)
        elif animation == 'Rainbow':
            from adafruit_led_animation.animation.rainbow import Rainbow
            self.led_animation = Rainbow(self.leds, speed=0.05)
