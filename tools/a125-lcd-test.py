#!/usr/bin/env python3
"""Test the front LCD (A125 panel on /dev/ttyS1, 1200 baud) of a QNAP TS-x39.

Run as root on the NAS:  python3 a125-lcd-test.py [/dev/ttyS1]

Turns the backlight on, writes two lines, then for 20 seconds prints every
message the panel sends (press ENTER and SELECT on the front). Protocol as
documented for other QNAP x86 models:
  4D 5E 0n          backlight off (n=0) / on (n=1)
  4D 0C ll 20 +16   write 16 characters on line ll (0 or 1)
  53 05 00 bb       button report: bb bit 0 = ENTER, bit 1 = SELECT
"""
import os
import select
import sys
import termios
import time


def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0                                    # iflag: raw
    attrs[1] = 0                                    # oflag: raw
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0                                    # lflag: raw
    attrs[4] = attrs[5] = termios.B1200
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def line(n, text):
    return bytes([0x4D, 0x0C, n, 0x20]) + text[:16].ljust(16).encode("ascii",
                                                                      "replace")


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyS1"
    fd = open_port(path)
    os.write(fd, bytes([0x4D, 0x5E, 0x01]))
    time.sleep(0.2)
    os.write(fd, line(0, "openmediavault"))
    time.sleep(0.2)
    os.write(fd, line(1, "LCD test OK"))
    print("Backlight on, two lines written. Press ENTER and SELECT for 20 s.")
    end = time.time() + 20
    while time.time() < end:
        ready, _, _ = select.select([fd], [], [], 0.5)
        if ready:
            data = os.read(fd, 64)
            print("received:", data.hex(" "))
    print("Done.")


if __name__ == "__main__":
    main()
