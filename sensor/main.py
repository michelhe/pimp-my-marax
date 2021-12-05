# This is your main script.

import time
import ujson
import machine
from machine import Pin, Timer

from marax import get_sensor

marax = get_sensor()


class PumpSensor(object):
    _PUMP_OFF_RETRY_COUNT = 10

    def __init__(self):
        self.pin = Pin(0, Pin.IN, Pin.PULL_UP)
        self.was_on = self.pin.value() == 0
        self.start_time = None
        self.retries = self._PUMP_OFF_RETRY_COUNT

    def reset_retries(self):
        self.retries = self._PUMP_OFF_RETRY_COUNT

    def shot_timer_elapsed(self):
        if self.start_time is not None:
            return (time.ticks_ms() - self.start_time) // 1000
        return None

    def start_shot_timer(self):
        print('[PUMP]: Pump detected! starting timer')
        self.start_time = time.ticks_ms()
        self.retries = self._PUMP_OFF_RETRY_COUNT

    def stop_shot_timer(self):
        elapsed = self.shot_timer_elapsed()
        print('[PUMP] Shot timer stopped after {}s'.format(elapsed))
        self.start_time = None
        self.retries = 0

    def check(self):
        now_on = self.pin.value() == 0
        was_on = self.was_on

        if now_on and not was_on:
            # detected pump started
            if self.start_time is None:
                self.start_shot_timer()
            else:
                print("[PUMP] Geesh I'm back!")
                self.reset_retries()
        if now_on:
            self.reset_retries()
        if not now_on and self.start_time is not None:
            print(
                '[PUMP] Timer is running but pump sensor off, retries left {}'.
                format(self.retries))
            self.retries -= 1
            if self.retries <= 0:
                self.stop_shot_timer()

        self.was_on = now_on


pump = PumpSensor()

UPDATE_INTERVAL_MS = 2000
last_update_ticks = time.ticks_ms() - UPDATE_INTERVAL_MS

reported_offline = True

marax.connect()
print('listening for data on MaraX uart..')

last_result = None


def wait_for_activity():
    while True:
        line = marax.recv_line()
        if line is not None:
            # It's okay to drop the line, we'll grab the next one
            break
        time.sleep_ms(1000)


last_good_result = None
try:
    while True:
        pump.check()
        line = marax.recv_line()
        if line is None:
            if marax.is_offline():
                if mqtt is not None:
                    print('MaraX is offline!')
                    mqtt.publish(MQTT_TOPIC_STATUS, 'offline')
                    reported_offline = True
                    display.fill(0)
                    display.text("MaraX OFF", 0, 0, 1)
                    display.show()
                    time.sleep(10)
                    display.poweroff()
                    wait_for_activity()
            continue
        else:
            if reported_offline is not None and reported_offline:
                reported_offline = None
                mqtt.publish(MQTT_TOPIC_STATUS, 'online')
                print('MaraX is online!')
                display.poweron()
                display.fill(0)
                display.text("MaraX ON", 0, 0, 1)
                display.show()

        try:
            r = marax.parse(line)
            last_good_result = r
        except:
            print('parsing failure...')
            r = last_good_result
            if r is None:
                continue
        shot_timer_elapsed = pump.shot_timer_elapsed()
        # append the pump status to the resuly
        r["pump_on"] = shot_timer_elapsed is not None

        # publish to mqtt topic

        if mqtt is not None and time.ticks_ms() - last_update_ticks >= UPDATE_INTERVAL_MS:
            print('publishing')
            mqtt.publish(MQTT_TOPIC_SENSOR, ujson.dumps(r))
            last_update_ticks = time.ticks_ms()

        # update the display
        display.fill(0)
        display.text(
            "{} mode".format("Coffee" if r['mode'] == 'C' else 'Steam'), 0, 0,
            1)
        display.text("HX: {}".format(r['hx_temp']), 0, 10, 1)
        display.text(
            "Boiler: {}/{}".format(r['boiler_temp'], r['boiler_target']), 0,
            20, 1)
        if shot_timer_elapsed is not None:
            # also need to display the shot timer
            display.text('TIMER: ' + str(shot_timer_elapsed) + 's', 0, 64 - 20,
                         1)
        if r['heating_element_state'] == True:
            display.text("HEATING...", 0, 64 - 10, 1)

        display.show()
except Exception as e:
    display.fill(0)
    display.text("EXCEPTION!!!", 0, 10, 1)
    display.text(str(type(e).__name__), 0, 20, 1)
    display.show()
    t = Timer(-1)

    def bye_bye(t):
        machine.reset()

    t.init(mode=Timer.ONE_SHOT, period=10000, callback=bye_bye)
    raise
