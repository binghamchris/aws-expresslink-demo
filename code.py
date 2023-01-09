from demo_badge import Badge
from demo_badge.expresslink import Event
import json
from adafruit_ticks import ticks_add, ticks_less, ticks_ms

badge = Badge()
current_url=""
next_data_update = ticks_ms()
last_reported_state = {}
DEFAULT_UPDATE_RATE = 4000 # milliseconds
update_rate = DEFAULT_UPDATE_RATE

def change_url(url_to_share):
    global current_url
    print(f"Previous URL was: {current_url}")

    print(f"URL to share is: {url_to_share}")

    print("Setting NFC tag...")
    badge.nfc_tag.set_url(url_to_share)

    print("Displaying QR code...")
    badge.show_qr_code(url_to_share)

    current_url = url_to_share

    print(f"Current URL is: {current_url}")

    new_reported_state = report_changed_values(last_reported_state)
    last_reported_state.update(new_reported_state)


def handle_shadow_doc(line):
    if line.startswith("1 "):
        line = line[2:]
    elif line.startswith("0 "):
        print("ExpressLink SHADOW rejected:", line)
        return

    state = json.loads(line)['state']

    if 'desired' in state:
        # first: handle delta updates and unfinished desired
        handle_desired_shadow_state(state['desired'])
    elif 'reported' in state:
        # second: handle initial shadow doc from previous reported
        handle_desired_shadow_state(state['reported'])
    else:
        handle_desired_shadow_state(state)

def t2rgb(t): # convert RGB color to integer
    return t[0] << 16 | t[1] << 8 | t[2]

def handle_desired_shadow_state(desired_state):
    payload = {}
    payload['state'] = {}
    payload['state']['desired'] = {}
    payload['state']['reported'] = {}

    # Iterate over all desired state keys and update the Demo Badge components accordingly
    for k, v in desired_state.items():
        payload['state']['desired'][k] = None
        payload['state']['reported'][k] = v
        if k == 'display_brightness':
            badge.display.brightness = float(v) / 100
        elif k == 'shared_url':
            change_url(v)
        elif k == 'led_brightness':
            badge.leds.brightness = float(v) / 100
        elif k == 'led_animation':
            badge.set_led_animation(v)
            if v == 'Static':
                payload['state']['reported']['led_1'] = t2rgb(badge.leds[0])
                payload['state']['reported']['led_2'] = t2rgb(badge.leds[1])
                payload['state']['reported']['led_3'] = t2rgb(badge.leds[2])
                payload['state']['reported']['led_4'] = t2rgb(badge.leds[3])
                payload['state']['reported']['led_5'] = t2rgb(badge.leds[4])
        elif k == 'led_1':
            badge.leds[0] = v
        elif k == 'led_2':
            badge.leds[1] = v
        elif k == 'led_3':
            badge.leds[2] = v
        elif k == 'led_4':
            badge.leds[3] = v
        elif k == 'led_5':
            badge.leds[4] = v
        elif k == 'back_led':
            if v == 'on':
                badge.back_led.blink = None
                badge.back_led.value = True
            elif v == 'off':
                badge.back_led.blink = None
                badge.back_led.value = False
            elif v == 'blinking':
                badge.back_led.blink = True
        elif k == 'high_update_rate':
            global update_rate
            if v:
                badge.expresslink.debug = False
                update_rate = 100
                print("Using high update rate - going silent on ExpressLink command output.")
            else:
                badge.expresslink.debug = True
                update_rate = DEFAULT_UPDATE_RATE
                print("Using normal update rate - enabling ExpressLink command output for visibility.")

    # Publish that now everything is not only desired, but also active = reported
    badge.expresslink.shadow_update(json.dumps(payload))

def report_changed_values(last_reported_state):
    acceleration_x, acceleration_y, acceleration_z = badge.accelerometer.acceleration

    reported_state = {}

    def conditional_report(name, value):
        if name not in last_reported_state or last_reported_state[name] != value:
            reported_state[name] = value

    conditional_report('temperature', badge.temperature_humidity.temperature)
    conditional_report('humidity', badge.temperature_humidity.relative_humidity)
    conditional_report('ambient_light', float(badge.ambient_light.value))
    conditional_report('acceleration_x', acceleration_x)
    conditional_report('acceleration_y', acceleration_y)
    conditional_report('acceleration_z', acceleration_z)
    conditional_report('button_1', 'pressed' if not badge.button1.value else 'not pressed')
    conditional_report('button_2', 'pressed' if not badge.button2.value else 'not pressed')
    conditional_report('button_3', 'pressed' if not badge.button3.value else 'not pressed')
    conditional_report('led_1', t2rgb(badge.leds[0]))
    conditional_report('led_2', t2rgb(badge.leds[1]))
    conditional_report('led_3', t2rgb(badge.leds[2]))
    conditional_report('led_4', t2rgb(badge.leds[3]))
    conditional_report('led_5', t2rgb(badge.leds[4]))
    conditional_report('shared_url', current_url)

    # Publish shadow update
    payload = {}
    payload['state'] = {}
    payload['state']['reported'] = reported_state
    badge.expresslink.shadow_update(json.dumps(payload))

    return reported_state


# Connect to AWS, stop if there is any error
success, status, err = badge.expresslink.connect()
if not success:
    print(f"Unable to connect: {err} {status}")
    while True: pass

change_url("https://cloudypandas.ch")

thing_name = badge.expresslink.config.ThingName
badge.expresslink.config.enable_shadow = True
badge.expresslink.shadow_init()
badge.expresslink.shadow_doc()
badge.expresslink.shadow_subscribe()



while True:
    badge.update()

    while badge.expresslink.event_signal.value:
        badge.update()

        event_id, parameter, mnemonic, detail = badge.expresslink.get_event()
        if not event_id:
            pass # no event pending
        elif event_id == Event.SHADOW_DOC:
            success, line, err = badge.expresslink.shadow_get_doc()
            handle_shadow_doc(line)
        elif event_id == Event.SHADOW_DELTA:
            success, line, err = badge.expresslink.shadow_get_delta()
            handle_shadow_doc(line)
        elif event_id == Event.SHADOW_UPDATE:
            t = badge.expresslink.debug
            badge.expresslink.debug = False
            success, line, err = badge.expresslink.shadow_get_update()
            badge.expresslink.debug = t
            # shadow update accepted, no further processing needed
        else:
            print(f"Ignoring event: {event_id} {parameter} {mnemonic} {detail}")

    if ticks_less(next_data_update, ticks_ms()):
        new_reported_state = report_changed_values(last_reported_state)
        last_reported_state.update(new_reported_state)

        # set the next data update timestamp
        next_data_update = ticks_add(ticks_ms(), update_rate)

    if badge.button1.pressed:
        change_url("https://cloudypandas.ch")
    if badge.button2.pressed:
        change_url("https://www.cloudreach.com/en/technical-blog/")
    if badge.button3.pressed:
        change_url("https://github.com/binghamchris")
    