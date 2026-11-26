#!/usr/bin/env python3
"""Find how to turn on the front LCD backlight (QNAP TS-x39).

Run as root on the NAS, looking at the LCD:  python3 a125-lcd-wake.py

Step 1 sends the backlight-on command (4D 5E 01) several times, slowly.
Step 2 (only if step 1 did nothing) flips, one at a time, the IT8718F
output pins that showed nothing in the LED probe, sends the backlight
command again, and asks what the LCD did. Every pin is put back.
"""
import os
import sys
import termios
import time

CANDIDATES = ["GP10", "GP11", "GP12", "GP13", "GP14", "GP27", "GP32",
              "GP33"]
BASE = 0x0A20  # Simple I/O base on the TS-639 Pro


def open_lcd(path="/dev/ttyS1"):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B1200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def wake(fd):
    for _ in range(3):
        os.write(fd, bytes([0x4D, 0x5E, 0x01]))
        termios.tcdrain(fd)
        time.sleep(0.5)
    for n, text in ((0, "openmediavault"), (1, "LCD test OK")):
        os.write(fd, bytes([0x4D, 0x0C, n, 0x20]) + text.ljust(16).encode())
        termios.tcdrain(fd)
        time.sleep(0.3)


class Port:
    def __init__(self):
        self.fd = os.open("/dev/port", os.O_RDWR)

    def outb(self, addr, value):
        os.lseek(self.fd, addr, os.SEEK_SET)
        os.write(self.fd, bytes([value]))

    def inb(self, addr):
        os.lseek(self.fd, addr, os.SEEK_SET)
        return os.read(self.fd, 1)[0]


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    lcd = open_lcd()
    print("Step 1: backlight on, 3 times, then two lines of text.")
    wake(lcd)
    if input("Is the LCD lit or showing text now? [y/N] ").strip().lower() \
            in ("y", "s", "yes", "sim"):
        print("Good: no pin needed.")
        return
    io = Port()
    with open("a125-lcd-wake.log", "a") as log:
        for name in CANDIDATES:
            s, bit = int(name[2]), int(name[3])
            addr = BASE + s - 1
            before = io.inb(addr)
            input("\n%s: look at the LCD, then press Enter..." % name)
            try:
                io.outb(addr, before ^ (1 << bit))
                time.sleep(1)
                wake(lcd)
                time.sleep(1)
            finally:
                io.outb(addr, before)
            seen = input("  What did the LCD do? (Enter = nothing) ").strip()
            log.write("%s: %s\n" % (name, seen or "nothing"))
            log.flush()
            if seen:
                break
    print("Done. Results in %s" % os.path.abspath("a125-lcd-wake.log"))


if __name__ == "__main__":
    main()
