# Create a config.py file in the same directory and make sure to configure the following constants
from config import WIFI_SSID, WIFI_PASSWORD

import time
import machine
import micropython
import network
import esp
esp.osdebug(None)
import gc
gc.collect()

sta = network.WLAN(network.STA_IF)
sta.active(True)
sta.connect(WIFI_SSID, WIFI_PASSWORD)

print('Connecting to {}...'.format(WIFI_SSID))
  
while sta.isconnected() == False:
  time.sleep(1)

print('Connected!')
print(sta.ifconfig())