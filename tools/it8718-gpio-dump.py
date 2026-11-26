#!/usr/bin/env python3
"""Read-only dump of the IT8718F GPIO configuration (QNAP TS-x39).

Run as root on the NAS:  python3 it8718-gpio-dump.py

It changes no pin. It only enters the Super I/O configuration mode (the
same key sequence sensors-detect and the it87 driver use), reads registers,
and leaves configuration mode again. Then it reads the current value of
each GPIO set from the Simple I/O ports.
"""
import os
import sys

PORTS = [(0x2E, bytes([0x87, 0x01, 0x55, 0x55])),
         (0x4E, bytes([0x87, 0x01, 0x55, 0xAA]))]


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
    io = Port()
    for idx, key in PORTS:
        for b in key:
            io.outb(idx, b)

        def reg(r):
            io.outb(idx, r)
            return io.inb(idx + 1)

        chip = (reg(0x20) << 8) | reg(0x21)
        if chip != 0x8718:
            io.outb(idx, 0x02)
            io.outb(idx + 1, 0x02)
            continue
        print("IT8718F at config port 0x%02X, revision %d" % (idx, reg(0x22) & 0x0F))
        func = [reg(0x25 + i) for i in range(5)]       # global: pin = GPIO?
        io.outb(idx, 0x07)
        io.outb(idx + 1, 0x07)                          # LDN 7: GPIO
        base = (reg(0x62) << 8) | reg(0x63)
        pol = [reg(0xB0 + i) for i in range(5)]
        pull = [reg(0xB8 + i) for i in range(5)]
        simple = [reg(0xC0 + i) for i in range(5)]
        outen = [reg(0xC8 + i) for i in range(5)]
        # Hardware LED blink: pin location (set << 3 | bit) and control.
        blink = [(reg(0xF8), reg(0xF9)), (reg(0xFA), reg(0xFB))]
        io.outb(idx, 0x02)
        io.outb(idx + 1, 0x02)                          # leave config mode
        print("Simple I/O base: 0x%04X" % base)
        for n, (loc, ctl) in enumerate(blink, 1):
            where = "GP%d%d" % (loc >> 3 & 7, loc & 7) if loc else "none"
            print("LED blink %d: pin %s (location 0x%02X, control 0x%02X)"
                  % (n, where, loc, ctl))
        vals = [io.inb(base + i) if base else None for i in range(5)]
        print()
        print("pin   gpio  simple  dir  inverted  pullup  value")
        for s in range(5):
            for bit in range(8):
                m = 1 << bit
                if not func[s] & m:
                    continue
                print("GP%d%d   yes   %-6s  %-3s  %-8s  %-6s  %s" % (
                    s + 1, bit,
                    "yes" if simple[s] & m else "no",
                    "out" if outen[s] & m else "in",
                    "yes" if pol[s] & m else "no",
                    "yes" if pull[s] & m else "no",
                    "-" if vals[s] is None else (1 if vals[s] & m else 0)))
        print()
        print("raw: func=%s simple=%s out=%s pol=%s values=%s" % (
            [hex(x) for x in func], [hex(x) for x in simple],
            [hex(x) for x in outen], [hex(x) for x in pol],
            [hex(x) for x in vals if x is not None]))
        return
    sys.exit("No IT8718F found on config port 0x2E or 0x4E.")


if __name__ == "__main__":
    main()
