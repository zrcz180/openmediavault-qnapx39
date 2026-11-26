#!/usr/bin/env python3
"""Does the LCD stay lit with GP10 = 0 and one command? (QNAP TS-639 Pro)

Run as root on the NAS, looking at the LCD:  python3 a125-lcd-steady.py

1. Lists any other process that has /dev/ttyS1 open (it could fight us).
2. Sets GP10 = 0, sends backlight on ONCE and the text ONCE, then sends
   nothing for 20 s. Watch whether the light and text stay.
3. Asks whether to leave GP10 = 0 (so you can keep watching) or put it back.
"""
import os
import sys
import termios
import time

ADDR, BIT = 0x0A20, 0  # GP10
TTY = "/dev/ttyS1"


def others_on_tty():
    found = []
    real = os.path.realpath(TTY)
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            fds = os.listdir("/proc/%s/fd" % pid)
            for fd in fds:
                if os.path.realpath("/proc/%s/fd/%s" % (pid, fd)) == real:
                    with open("/proc/%s/comm" % pid) as f:
                        found.append("%s (pid %s)" % (f.read().strip(), pid))
                    break
        except OSError:
            pass
    return found


def open_lcd():
    fd = os.open(TTY, os.O_RDWR | os.O_NOCTTY)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0
    a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    a[4] = a[5] = termios.B1200
    termios.tcsetattr(fd, termios.TCSANOW, a)
    return fd


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    users = others_on_tty()
    print("Other processes using %s: %s" % (TTY, ", ".join(users) or "none"))
    lcd = open_lcd()
    port = os.open("/dev/port", os.O_RDWR)
    os.lseek(port, ADDR, os.SEEK_SET)
    before = os.read(port, 1)[0]
    keep = False
    try:
        input("Press Enter and watch the LCD for 20 s...")
        os.lseek(port, ADDR, os.SEEK_SET)
        os.write(port, bytes([before & ~(1 << BIT)]))
        time.sleep(0.5)
        os.write(lcd, bytes([0x4D, 0x5E, 0x01]))
        termios.tcdrain(lcd)
        time.sleep(0.2)
        os.write(lcd, bytes([0x4D, 0x0C, 0, 0x20]) + b"openmediavault  " +
                 bytes([0x4D, 0x0C, 1, 0x20]) + b"LCD test OK     ")
        termios.tcdrain(lcd)
        for s in range(20, 0, -5):
            print("  %d s left..." % s)
            time.sleep(5)
        keep = input("Leave GP10 = 0 so the LCD stays as it is? [y/N] ") \
            .strip().lower() == "y"
    finally:
        if not keep:
            os.lseek(port, ADDR, os.SEEK_SET)
            os.write(port, bytes([before | (1 << BIT)]))  # GP10 is 1 at boot
            print("GP10 back to 1 (boot value).")
        else:
            print("GP10 left at 0. Run again and answer N to restore.")


if __name__ == "__main__":
    main()
