# This is your main script.

import time
import ujson
import ubinascii
import machine
import select
from machine import Pin, SoftUART

from config import MARAX_TX, MARAX_RX, MQTT_BROKER, MQTT_USER, MQTT_PASS, MQTT_TOPIC
from umqttsimple import MQTTClient

poll = select.poll()

# Create SoftUART device
uart = SoftUART(tx=Pin(MARAX_TX), rx=Pin(MARAX_RX), baudrate=9600)
poll.register(uart)

# Create MQTT Client
if MQTT_BROKER:
    client_id = ubinascii.hexlify(machine.unique_id())
    mqtt = MQTTClient(client_id, MQTT_BROKER, user=MQTT_USER, password=MQTT_PASS)

while True:
    try:
        print('Connecting to MQTT broker: {}'.format(MQTT_BROKER))
        mqtt.connect()
    except Exception as e:
        print('Connection failed, trying again in a few seconds..')
        time.sleep(10)
    else:
        break

def parse_line(line):
    orig_line = line
    assert line is not None
    mode = line[0:1]
    assert mode in ('C', 'V'), "unknown mode: {}".format(mode)

    line = line[1:].split(',')

    result = {}
    assert len(line) == 6, "unknown line: {}".format(orig_line)
    result['mode'] = mode
    result['gicarVw'] = line[0]
    result['boiler_temp'] = int(line[1])
    result['boiler_target'] = int(line[2])
    result['hx_temp'] = int(line[3])
    result['countdown'] = int(line[4])
    result['heating_element_state'] = bool(line[5])

    return result


last_update_ticks = time.ticks_ms()
UPDATE_INTERVAL_MS = 1000

print('listening for data on MaraX uart..')
while True:
    read = poll.ipoll()

    for r, ev in read:
        if (ev & select.POLLIN) == 0:
            continue
        line = r.readline()
        if not line:
            continue
        try:
            line = line.decode('ascii')
        except UnicodeError:
            continue  # software uart bugs sometimes

        # preparse line to avoid actually doing the parsing again :(
        if line[0] not in ('C', 'V'):
            continue

        # do not parse *every line*
        if time.ticks_ms() < last_update_ticks + UPDATE_INTERVAL_MS:
            continue

        last_update_ticks = time.ticks_ms()
        try:
            result = parse_line(line)
            print(result)
        except Exception as e:
            print("Failed to parse line: {}, error={}".format(line, e))
            continue

        # publish to mqtt topic
        if MQTT_BROKER:
            mqtt.connect()  # wouldn't harm to re-connect, eh?
            mqtt.publish(MQTT_TOPIC, ujson.dumps(result))


    # TODO; Need to investigate if Mpy port for esp8266 actually supports sleep or only does a busy-wait.
