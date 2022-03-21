import time
from config import MARAX_TX, MARAX_RX, MOCK_SETUP
from machine import Pin, SoftUART

import select

poll = select.poll()

sensor = None


def get_sensor():
    global sensor
    if sensor is None:
        if MOCK_SETUP:

            class MockMaraxSensor(MaraxSensor):
                def connect(self):
                    pass

                def recv_line(self):
                    return 'C123b,112,124,97,0000,0\n'

            sensor = MockMaraxSensor()
        else:
            sensor = MaraxSensor()
    return sensor


class MaraxSensor(object):
    _TIMEOUT = 5000

    def __init__(self):
        self.last_line_time = time.ticks_ms()

    def connect(self):
        txpin = Pin(MARAX_TX)
        rxpin = Pin(MARAX_RX, Pin.IN, Pin.PULL_UP)
        print('setting up MaraX uart: TX={} RX={}'.format(txpin, rxpin))
        self.uart = SoftUART(tx=Pin(MARAX_TX), rx=Pin(MARAX_RX), baudrate=9600)
        poll.register(self.uart)

    def recv_line(self):
        read = poll.ipoll()
        lines = []
        for r, ev in read:
            if (ev & select.POLLIN) == 0:
                continue
            line = r.readline()
            if not line:
                print('failed to get line from uart')
                continue
            try:
                line = line.decode('ascii')
            except UnicodeError:
                print('failed to decode line:')
                print(line)
                continue  # software uart bugs sometimes

            lines.append(line)
        if lines:
            # since this is realtime data, only the last line will suffice.
            self.last_line_time = time.ticks_ms()
            return lines[-1]
        else:
            return None

    def is_offline(self):
        return time.ticks_ms() - self.last_line_time > self._TIMEOUT

    # See this post for differences between maraX V1 & V2:
    # https://coffeetime.freeflarum.com/d/417-lelit-mara-x-v1-and-v2-the-differences
    #
    # In short, an old machine can be upgraded to V2 if you swap the gicar for a V2 one (like I did)
    # The V2 gicar is programmed differently and now the side switches mean different things
    # mode I - now called "xmode steam" maintains a stable HX temp and does steam boost after the shot
    # mode O - was steam priority mode in V1, now the O position is called "xmode_coffee" and the function is entirely different.
    #          it tries to maintain as constant and stable HX temp as possible, thus *not* activating steam boost at all.
    #          use it if you want to brew some speciality coffee :P
    mode_map = {
        "v1": {"C": "coffee_mode", "V": "steam_mode"},
        "v2": {"C": "xmode_steam", "+": "xmode_coffee"}
    }

    def _parse_common(self, output: dict, metrics: list[str]):
        output['firmare_version'] = metrics[0]
        output['boiler_temp'] = int(metrics[1])
        output['boiler_target'] = int(metrics[2])
        output['hx_temp'] = int(metrics[3])
        output['countdown'] = int(metrics[4])
        output['heating_element_state'] = int(metrics[5])

    def _parse_v1(self, mode: str, metrics: list[str]) -> dict:
        result = {"marax_version": "v1"}
        self._parse_common(result, metrics)
        modes = self.mode_map['v1']
        assert mode in modes,  "no such mode: {}".format(mode)
        result['mode'] = modes[mode]
        return result

    def _parse_v2(self, mode: str, metrics: list[str]) -> dict:
        result = {"marax_version": "v2"}
        self._parse_common(result, metrics)
        modes = self.mode_map['v2']
        result['mode'] = modes.get(mode, 'unknown: {}'.format(mode))
        # MaraX v2 gicar emits one more metric, currently unknown
        result['unknown'] = int(metrics[6])
        return result

    def parse(self, line):
        orig_line = line
        assert line is not None
        mode = line[0:1]

        metrics = line[1:].rstrip('\r\n').rstrip('\n').split(',')
        if len(metrics) == 6:
            return self._parse_v1(mode, metrics)
        elif len(metrics) == 7:
            return self._parse_v2(mode, metrics)
        else:
            raise RuntimeError("unknown line: {}".format(orig_line))