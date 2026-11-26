#!/usr/bin/env python3
"""Find which IT8718F GPIO pin drives which LED (QNAP TS-x39).

Run as root on the NAS, with the NAS idle, while looking at the front:

    python3 it8718-gpio-probe.py              # all candidate pins
    python3 it8718-gpio-probe.py GP30 GP31    # only these

For each pin it flips the output for a short time, puts it back, and asks
what changed on the front panel. Answers go to it8718-gpio-probe.log.
Only pins that are already Simple I/O outputs are touched. Every pin is
restored, also on Ctrl-C or an error.
"""
import os
import sys
import time

CONFIG = 0x2E
KEY = bytes([0x87, 0x01, 0x55, 0x55])
SECONDS = 1.5
# Asked for confirmation first: a 6-pin group that could also be disk power.
CAREFUL = {"GP30", "GP31", "GP32", "GP33", "GP34", "GP35"}
LOG = "it8718-gpio-probe.log"


class Port:
    def __init__(self):
        self.fd = os.open("/dev/port", os.O_RDWR)

    def outb(self, addr, value):
        os.lseek(self.fd, addr, os.SEEK_SET)
        os.write(self.fd, bytes([value]))

    def inb(self, addr):
        os.lseek(self.fd, addr, os.SEEK_SET)
        return os.read(self.fd, 1)[0]


def read_config(io):
    for b in KEY:
        io.outb(CONFIG, b)

    def reg(r):
        io.outb(CONFIG, r)
        return io.inb(CONFIG + 1)

    try:
        if (reg(0x20) << 8 | reg(0x21)) != 0x8718:
            sys.exit("No IT8718F on config port 0x2E.")
        func = [reg(0x25 + i) for i in range(5)]
        io.outb(CONFIG, 0x07)
        io.outb(CONFIG + 1, 0x07)
        base = reg(0x62) << 8 | reg(0x63)
        simple = [reg(0xC0 + i) for i in range(5)]
        outen = [reg(0xC8 + i) for i in range(5)]
    finally:
        io.outb(CONFIG, 0x02)
        io.outb(CONFIG + 1, 0x02)
    pins = []
    for s in range(5):
        for bit in range(8):
            m = 1 << bit
            if func[s] & simple[s] & outen[s] & m:
                pins.append(("GP%d%d" % (s + 1, bit), s, bit))
    return base, pins


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    io = Port()
    base, pins = read_config(io)
    if not base:
        sys.exit("Simple I/O base is not set.")
    wanted = [a.upper() for a in sys.argv[1:]]
    if wanted:
        unknown = set(wanted) - {p[0] for p in pins}
        if unknown:
            sys.exit("Not Simple I/O outputs, not touched: %s" %
                     " ".join(sorted(unknown)))
        pins = [p for p in pins if p[0] in wanted]
    print("Pins to test: %s" % " ".join(p[0] for p in pins))
    print("Each one changes for %.1f s, then goes back.\n" % SECONDS)
    with open(LOG, "a") as log:
        for name, s, bit in pins:
            if name in CAREFUL and not wanted:
                answer = input("%s may be disk power. Test it? [y/N] " % name)
                if answer.strip().lower() not in ("y", "s", "yes", "sim"):
                    log.write("%s skipped\n" % name)
                    continue
            addr = base + s
            before = io.inb(addr)
            input("%s (now %d): look at the front, then press Enter... "
                  % (name, before >> bit & 1))
            try:
                io.outb(addr, before ^ (1 << bit))
                time.sleep(SECONDS)
            finally:
                io.outb(addr, before)
            seen = input("  What changed? (Enter = nothing, r = repeat) ")
            while seen.strip().lower() == "r":
                try:
                    io.outb(addr, before ^ (1 << bit))
                    time.sleep(SECONDS)
                finally:
                    io.outb(addr, before)
                seen = input("  What changed? (Enter = nothing, r = repeat) ")
            log.write("%s was %d: %s\n" % (name, before >> bit & 1,
                                           seen.strip() or "nothing"))
            log.flush()
    print("\nDone. Results in %s" % os.path.abspath(LOG))


if __name__ == "__main__":
    main()
