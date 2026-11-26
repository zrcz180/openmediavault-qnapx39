#!/usr/bin/env python3
"""Check what stops the Status LED from blinking (QNAP TS-x39).

Run as root on the NAS, looking at the Status LED:
    python3 it8718-blink-test.py

The BIOS maps the IT8718F blink generator 1 to a pin (GP26 on a TS-639
Pro). This unmaps it for 5 seconds, then puts it back. It changes only the
blink mapping register; every value is restored, also on Ctrl-C.
"""
import os
import sys
import time

INDEX, KEY = 0x2E, bytes([0x87, 0x01, 0x55, 0x55])


class Port:
    def __init__(self):
        self.fd = os.open("/dev/port", os.O_RDWR)

    def outb(self, addr, value):
        os.lseek(self.fd, addr, os.SEEK_SET)
        os.write(self.fd, bytes([value]))

    def inb(self, addr):
        os.lseek(self.fd, addr, os.SEEK_SET)
        return os.read(self.fd, 1)[0]


def config(io, writes=()):
    """Enter config mode, select LDN 7, apply writes, return F8/F9."""
    for b in KEY:
        io.outb(INDEX, b)
    try:
        io.outb(INDEX, 0x07)
        io.outb(INDEX + 1, 0x07)
        for reg, value in writes:
            io.outb(INDEX, reg)
            io.outb(INDEX + 1, value)
        result = []
        for reg in (0xF8, 0xF9):
            io.outb(INDEX, reg)
            result.append(io.inb(INDEX + 1))
        return result
    finally:
        io.outb(INDEX, 0x02)
        io.outb(INDEX + 1, 0x02)


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    io = Port()
    loc, ctl = config(io)
    print("Blink 1: location 0x%02X, control 0x%02X" % (loc, ctl))
    if not loc:
        sys.exit("Blink 1 is not mapped to any pin; nothing to test.")
    input("Look at the Status LED and press Enter...")
    try:
        config(io, [(0xF8, 0x00)])
        print("Blink unmapped for 5 s: what does the Status LED do?")
        time.sleep(5)
    finally:
        config(io, [(0xF8, loc), (0xF9, ctl)])
    print("Restored (location 0x%02X, control 0x%02X)." % tuple(config(io)))


if __name__ == "__main__":
    main()
