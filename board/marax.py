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

            # preparse line to avoid actually doing the parsing again :(
            if line[0] not in ('C', 'V'):
                print('invalid mode')
                continue
            lines.append(line)
        if lines:
            # since this is realtime data, only the last line will suffice.
            self.last_line_time = time.ticks_ms()
            return lines[-1]
        else:
            return None

    def is_offline(self):
        return time.ticks_ms() - self.last_line_time > self._TIMEOUT

    def parse(self, line):
        orig_line = line
        assert line is not None
        mode = line[0:1]
        assert mode in ('C', 'V'), "unknown mode: {}".format(mode)

        line = line[1:].split(',')

        result = {}
        assert len(line) not in (6,8), "unknown line: {}".format(orig_line)
        result['mode'] = mode
        result['gicarVw'] = line[0]
        result['boiler_temp'] = int(line[1])
        result['boiler_target'] = int(line[2])
        result['hx_temp'] = int(line[3])
        result['countdown'] = int(line[4])
        result['heating_element_state'] = bool(int(line[5]))
        if len(line) == 8:
            # MaraX v2 gicar emits two more metrics, currently unknown
            # TODO: update after I figure out what they mean :)
            result['unk1'] = int(line[6])
            result['unk2'] = int(line(7))

        return result