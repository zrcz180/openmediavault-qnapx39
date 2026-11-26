#!/usr/bin/env python3
"""Find the USB Copy and Reset buttons and the beeper (QNAP TS-639 Pro).

Run as root on the NAS, next to it:  python3 ts639-buttons-beep-test.py

Part 1, beeper: sounds the PC speaker (timer channel 2, port 0x61) for
half a second. Say whether you heard it.
Part 2, buttons: for 40 s, prints every change on the IT8718F GPIO input
pins. Press USB Copy a few times, then Reset (short presses only: the
plugin is not running, so nothing happens). Nothing is written to any
GPIO pin.
"""
import os
import sys
import time

IDX = 0x2E
KEY = bytes([0x87, 0x01, 0x55, 0x55])


class Port:
    def __init__(self):
        self.fd = os.open("/dev/port", os.O_RDWR)

    def outb(self, addr, value):
        os.lseek(self.fd, addr, os.SEEK_SET)
        os.write(self.fd, bytes([value]))

    def inb(self, addr):
        os.lseek(self.fd, addr, os.SEEK_SET)
        return os.read(self.fd, 1)[0]


def beep(io, hz=1000, seconds=0.5):
    divisor = 1193182 // hz
    io.outb(0x43, 0xB6)                 # channel 2, square wave
    io.outb(0x42, divisor & 0xFF)
    io.outb(0x42, divisor >> 8)
    old = io.inb(0x61)
    io.outb(0x61, old | 0x03)           # gate + speaker on
    try:
        time.sleep(seconds)
    finally:
        io.outb(0x61, old & ~0x03 & 0xFF)


def gpio_layout(io):
    for b in KEY:
        io.outb(IDX, b)

    def reg(r):
        io.outb(IDX, r)
        return io.inb(IDX + 1)

    chip = reg(0x20) << 8 | reg(0x21)
    func = [reg(0x25 + i) for i in range(5)]
    io.outb(IDX, 0x07)
    io.outb(IDX + 1, 0x07)
    base = reg(0x62) << 8 | reg(0x63)
    simple = [reg(0xC0 + i) for i in range(5)]
    outen = [reg(0xC8 + i) for i in range(5)]
    io.outb(IDX, 0x02)
    io.outb(IDX + 1, 0x02)
    if chip != 0x8718 or not base:
        sys.exit("No IT8718F GPIO found (chip 0x%04X)." % chip)
    # Inputs: GPIO function, Simple I/O, not an output.
    inputs = [func[s] & simple[s] & ~outen[s] & 0xFF for s in range(5)]
    return base, inputs


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    io = Port()
    input("Part 1: press Enter and listen for a beep...")
    beep(io)
    print("  Did you hear a beep? (tell Claude)")
    base, inputs = gpio_layout(io)
    pins = ["GP%d%d" % (s + 1, b) for s in range(5) for b in range(8)
            if inputs[s] >> b & 1]
    print("\nInput pins watched: " + ", ".join(pins))
    input("Part 2: press Enter, then press USB Copy 3 times, wait, "
          "then Reset 3 times (40 s)...")
    last = [io.inb(base + s) for s in range(5)]
    start = time.time()
    while time.time() - start < 40:
        now = [io.inb(base + s) for s in range(5)]
        for s in range(5):
            changed = (now[s] ^ last[s]) & inputs[s]
            for b in range(8):
                if changed >> b & 1:
                    print("%6.2f s  GP%d%d -> %d" % (time.time() - start,
                                                     s + 1, b,
                                                     now[s] >> b & 1))
        last = now
        time.sleep(0.02)
    print("Done. Send Claude everything printed above.")


if __name__ == "__main__":
    main()
