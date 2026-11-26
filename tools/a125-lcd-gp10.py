#!/usr/bin/env python3
"""Hold GP10 low for 20 s and drive the LCD (QNAP TS-639 Pro).

Run as root on the NAS, looking at the LCD:  python3 a125-lcd-gp10.py

GP10 flipped to 0 made the LCD flash with the backlight command, so it
may power the panel. This keeps it at 0 for 20 s: backlight on once,
two lines of text, the backlight off and on again, then puts GP10 back.
"""
import os
import sys
import termios
import time

BASE = 0x0A20
SET, BIT = 1, 0  # GP10


def open_lcd(path="/dev/ttyS1"):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B1200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def send(fd, data, note):
    os.write(fd, bytes(data))
    termios.tcdrain(fd)
    print("  %s" % note, flush=True)


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    lcd = open_lcd()
    port = os.open("/dev/port", os.O_RDWR)
    addr = BASE + SET - 1
    os.lseek(port, addr, os.SEEK_SET)
    before = os.read(port, 1)[0]
    try:
        os.lseek(port, addr, os.SEEK_SET)
        os.write(port, bytes([before & ~(1 << BIT)]))
        print("GP10 = 0. Watch the LCD:", flush=True)
        time.sleep(1)
        send(lcd, [0x4D, 0x5E, 0x01], "t=1 s  backlight on")
        time.sleep(1)
        send(lcd, [0x4D, 0x0C, 0, 0x20] + list(b"openmediavault  "),
             "t=2 s  line 1: openmediavault")
        time.sleep(0.5)
        send(lcd, [0x4D, 0x0C, 1, 0x20] + list(b"LCD test OK     "),
             "t=3 s  line 2: LCD test OK")
        time.sleep(7)
        send(lcd, [0x4D, 0x5E, 0x00], "t=10 s backlight off")
        time.sleep(3)
        send(lcd, [0x4D, 0x5E, 0x01], "t=13 s backlight on")
        time.sleep(7)
    finally:
        os.lseek(port, addr, os.SEEK_SET)
        os.write(port, bytes([before]))
        print("GP10 restored to %d." % (before >> BIT & 1))


if __name__ == "__main__":
    main()
