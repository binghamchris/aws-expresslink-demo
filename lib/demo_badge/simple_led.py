import digitalio
from adafruit_ticks import ticks_add, ticks_less, ticks_ms

class SimpleLED:
    def __init__(self, pin, blink_delay_ms: int=250) -> None:
        self.o = digitalio.DigitalInOut(pin)
        self.o.direction = digitalio.Direction.OUTPUT
        self.pin = pin
        self.blink = False
        self.blink_delay_ms = blink_delay_ms
        self._next_blink_change = ticks_ms()

    @property
    def value(self):
        return self.o.value

    @value.setter
    def value(self, v):
        self.o.value = v

    def update(self):
        if not ticks_less(self._next_blink_change, ticks_ms()):
            return

        if isinstance(self.blink, (int, float)):
            if self.blink > 0:
                self.blink -= 0.5
                self.o.value = not self.o.value
            else:
                self.blink = None
                self.o.value = False
        elif self.blink:
            self.o.value = not self.o.value
        else:
            self.blink = None

        self._next_blink_change = ticks_add(ticks_ms(), self.blink_delay_ms)
