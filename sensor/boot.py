# Create a config.py file in the same directory and make sure to configure the following constants
from config import WEBREPL_PORT, WIFI_SSID, WIFI_PASSWORD
from config import MOCK_SETUP, MQTT_BROKER, MQTT_USER, MQTT_PASS
from config import WEBREPL_ENABLED, WEBREPL_PASSWORD
import time
import machine
import micropython
import network
import esp
import ubinascii

from machine import Pin, I2C
import ssd1306

esp.osdebug(None)
import gc

gc.collect()

# using default address 0x3C
i2c = I2C(sda=Pin(4), scl=Pin(5))
display = ssd1306.SSD1306_I2C(128, 64, i2c)
display.fill(0)
display.text("Starting...", 0, 0, 1)
display.show()

sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(WIFI_SSID, WIFI_PASSWORD)

print('Connecting to {}...'.format(WIFI_SSID))

while sta.isconnected() == False:
    time.sleep(1)

print('Connected!')
ifconfig = sta.ifconfig()
print(sta.ifconfig())

display.fill(0)
display.text("Hello,", 0, 0, 1)
display.text(WIFI_SSID, 0, 10, 1)
display.text(ifconfig[0], 0, 20, 1)
if WEBREPL_ENABLED:
    import webrepl
    port = WEBREPL_PORT or 8266
    password = WEBREPL_PASSWORD or 'CHANGEME!'  # <----------- This is the default password, please change it!
    webrepl.start(port=port, password=password)
    display.text("WEBREPL: {}".format(port), 0, 30, 1)
    display.text("PASS: {}".format(password), 0, 40, 1)

display.show()

try:
    import umqtt.robust
except ImportError:
    print('failed to find umqtt.robust package, using upip to install')
    import upip
    upip.install("micropython-umqtt.simple")
    upip.install("micropython-umqtt.robust")

# Create MQTT Client
mqtt = None
if MQTT_BROKER:
    try:
        from umqtt.robust import MQTTClient
    except ImportError:
        print(
            "WARNING: mqtt is configured but umqtt isn't installed, please install manually"
        )
    else:
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