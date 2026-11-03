#!/usr/bin/env python3
"""Hardware integration test only: inject a tap through the real evdev touch path."""
import os
import struct
import sys
import time
x, y = map(int, sys.argv[1:3])
assert 0 <= x <= 1024 and 0 <= y <= 600
with open('/sys/class/input/event1/device/name') as source:
    assert 'WaveShare' in source.read(), 'Identify the touchscreen before injection'
fd = os.open('/dev/input/event1', os.O_WRONLY)
def event(kind, code, value):
    os.write(fd, struct.pack('llHHi', 0, 0, kind, code, value))
try:
    for kind, code, value in [(3,47,0),(3,57,12345),(3,53,x),(3,54,y),(3,0,x),(3,1,y),(1,330,1),(0,0,0)]:
        event(kind, code, value)
    time.sleep(.12)
    for kind, code, value in [(3,47,0),(3,57,-1),(1,330,0),(0,0,0)]:
        event(kind, code, value)
finally:
    os.close(fd)
print(f'Injected evdev touch at {x}, {y}')
