#!/usr/bin/env python3
"""Does the LCD backlight need repeating? (QNAP TS-639 Pro)

Run as root on the NAS, looking at the LCD:  python3 a125-lcd-keepalive.py

Part A, GP10 as it is: backlight on every 0.5 s for 8 s.
Part B, GP10 = 0:      backlight on every 0.5 s for 8 s.
Part C, GP10 = 0:      text on both lines every 1 s for 6 s.
GP10 is put back at the end, also on Ctrl-C.
"""
import os
import sys
import termios
import time

ADDR, BIT = 0x0A20, 0  # GP10


def open_lcd(path="/dev/ttyS1"):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B1200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def repeat(fd, data, every, seconds):
    end = time.time() + seconds
    while time.time() < end:
        os.write(fd, bytes(data))
        termios.tcdrain(fd)
        time.sleep(every)


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    lcd = open_lcd()
    port = os.open("/dev/port", os.O_RDWR)
    os.lseek(port, ADDR, os.SEEK_SET)
    before = os.read(port, 1)[0]
    on = [0x4D, 0x5E, 0x01]
    try:
        input("Part A (GP10 unchanged): press Enter and watch the LCD...")
        repeat(lcd, on, 0.5, 8)
        input("Part B (GP10 = 0): press Enter and watch the LCD...")
        os.lseek(port, ADDR, os.SEEK_SET)
        os.write(port, bytes([before & ~(1 << BIT)]))
        repeat(lcd, on, 0.5, 8)
        print("Part C (GP10 = 0): text every second...")
        text = [0x4D, 0x0C, 0, 0x20] + list(b"openmediavault  ") + \
            [0x4D, 0x0C, 1, 0x20] + list(b"LCD test OK     ")
        repeat(lcd, on + text, 1, 6)
    finally:
        os.lseek(port, ADDR, os.SEEK_SET)
        os.write(port, bytes([before]))
        print("GP10 restored.")


if __name__ == "__main__":
    main()
