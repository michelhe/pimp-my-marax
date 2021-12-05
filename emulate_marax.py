'''
Sends the MaraX lines over a serial interface, useful for testing the sensor.
'''
import sys
import time

try:
    import serial
except ImportError:
    print('run: pip install pyserial', file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(
            'usage: python3 emulate_marax.py <PORT>\nExample: python3 emulate_marax.py /dev/ttyUSB1',
            file=sys.stderr)
        sys.exit(1)
    s = serial.Serial(port=sys.argv[1], baudrate=9600)
    try:
        while True:
            s.write(b'C123B,126,126,093,0000,0\n')
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('stopping...')
        s.close()
