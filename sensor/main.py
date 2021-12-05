# This is your main script.

import time
import ujson
import machine
from machine import Pin, Timer

from marax import get_sensor

marax = get_sensor()


class PumpSensor(object):
    def __init__(self):
        self.pin = Pin(0, Pin.IN, Pin.PULL_UP)
        self.old_value = self.pin.value()
        self.start_time = None

    def check(self):
        new_value = self.pin.value()

        if new_value == 0 and self.old_value == 1:
            print('Pump detected! starting timer')
            self.start_time = time.ticks_ms()

        elif new_value == 1 and self.old_value == 0:
            print('')
            self.start_time = None

        self.old_value = new_value
        if new_value == 0:
            return (time.ticks_ms() - self.start_time) // 1000
        return None


pump = PumpSensor()

last_update_ticks = None
UPDATE_INTERVAL_MS = 2000

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


try:
    while True:
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

        r = marax.parse(line)

        shot_timer_elapsed = pump.check()
        # append the pump status to the resuly
        r["pump_on"] = shot_timer_elapsed is not None

        # publish to mqtt topic

        if mqtt is not None and last_update_ticks is not None and time.ticks_ms(
        ) - last_update_ticks >= UPDATE_INTERVAL_MS:
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

        time.sleep_ms(100)
except Exception as e:
    display.fill(0)
    display.text("EXCEPTION!!!", 0, 10, 1)
    display.text(str(type(e).__name__), 0, 20, 1)
    display.show()
    time.sleep(10)
    machine.reset()