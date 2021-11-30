# This is your main script.

import time
import ujson
import ubinascii
import machine
from config import MOCK_SETUP, MQTT_BROKER, MQTT_USER, MQTT_PASS
from umqtt.robust import MQTTClient

from marax import get_sensor

marax = get_sensor()

# Create MQTT Client
mqtt = None
if MQTT_BROKER:
    MQTT_TOPIC_STATUS = b'marax/status'
    MQTT_TOPIC_SENSOR = b'marax/uart'
    if MOCK_SETUP:
        MQTT_TOPIC_SENSOR = b'mock_' + MQTT_TOPIC_SENSOR
        MQTT_TOPIC_STATUS = b'mock_' + MQTT_TOPIC_STATUS
    client_id = ubinascii.hexlify(machine.unique_id())
    mqtt = MQTTClient(client_id,
                      MQTT_BROKER,
                      user=MQTT_USER,
                      password=MQTT_PASS)

while True:
    try:
        print('Connecting to MQTT broker: {}'.format(MQTT_BROKER))
        mqtt.connect()
    except Exception as e:
        print('Connection failed, trying again in a few seconds..')
        time.sleep(10)
    else:
        break

last_update_ticks = time.ticks_ms()
UPDATE_INTERVAL_MS = 2000

reported_offline = True

marax.connect()
print('listening for data on MaraX uart..')
while True:
    line = marax.recv_line()
    if line is None:
        if marax.is_offline():
            if mqtt is not None:
                print('MaraX is offline!')
                reported_offline = True
                mqtt.publish(MQTT_TOPIC_STATUS, '{"online": false}')
                time.sleep(10)
        continue
    else:
        if reported_offline is not None and reported_offline:
            reported_offline = None
            mqtt.publish(MQTT_TOPIC_STATUS, '{"online": true}')
            print('MaraX is online!')

    # do not parse *every line*
    if time.ticks_ms() < last_update_ticks + UPDATE_INTERVAL_MS:
        continue

    try:
        result = marax.parse(line)
        print(result)
    except Exception as e:
        print("Failed to parse line: {}, error={}".format(line, e))
        continue

    # publish to mqtt topic
    if mqtt is not None:
        mqtt.publish(MQTT_TOPIC_SENSOR, ujson.dumps(result))
    last_update_ticks = time.ticks_ms()

    # TODO; Need to investigate if Mpy port for esp8266 actually supports sleep or only does a busy-wait.
