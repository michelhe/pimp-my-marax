# Hardware

I use a Wemos D1 Mini clone, and hook it up to the TX/RX connections in the MaraX. (see this [Reddit post](https://www.reddit.com/r/espresso/comments/hft5zv/data_visualisation_lelit_marax_mod/) for more information)

Display: SSD1306 compatible 0.96 OLED display (i2c)
Also attached a reed sensor to the pump but it doesn't seem to work yet.


# Installation

The upstream micropython builds do not include the SoftUART support for ESP8266, so I'm using this [MicroPython fork](https://github.com/MrJake222/micropython) meanwhile.
Building it is no easy feat since most Dockerfiles & Vagrants for provisioning the esp8266 sdk tools for micropython are broken in one way or another :/

Once you flash this MicroPython fork on your ESP, you'll need to create a `config.py` file in this directory and fill in some values, see [](config.py.template).

Make sure to `git submodules update --init` and run `./upload.sh` to upload all the micropython scripts to the ESP8266.

# MQTT

If you have an MQTT broker set up, you can configure `MQTT_BROKER` in `config.py` to its hostname and the sensor will publish the results to `marax/uart` topic.