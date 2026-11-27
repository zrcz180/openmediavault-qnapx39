#!/usr/bin/env python3
"""Find what makes the green disk LEDs blink on activity (QNAP TS-639 Pro).

Run as root on the NAS, with the plugin stopped, looking at the front:
    systemctl stop qnapx39d
    python3 disk-activity-led-test.py [bay]       (default bay 2)
    systemctl start qnapx39d

It reads the disk in that bay (read only, nothing is written to it) for
8 seconds in each step and asks whether its green LED blinked:
  1. as the BIOS left the chip (the plugin is stopped),
  2. with blink generator 1 unmapped from GP26, as the plugin does,
  3. flipping, one at a time, each output pin with no known use.
Every register is put back at the end, also on Ctrl-C.
"""
import os
import subprocess
import sys
import time

INDEX, KEY = 0x2E, bytes([0x87, 0x01, 0x55, 0x55])
BAYS = {1: "pci-0000:00:1f.1-ata-1", 2: "pci-0000:03:00.0-ata-2",
        3: "pci-0000:03:00.0-ata-3", 4: "pci-0000:03:00.0-ata-4",
        5: "pci-0000:04:00.0-ata-1", 6: "pci-0000:04:00.0-ata-2"}
UNKNOWN = [(1, 1), (1, 2), (1, 3), (1, 4), (2, 7), (3, 2), (3, 3)]


class Port:
    def __init__(self):
        self.fd = os.open("/dev/port", os.O_RDWR)

    def outb(self, addr, value):
        os.pwrite(self.fd, bytes([value]), addr)

    def inb(self, addr):
        return os.pread(self.fd, 1, addr)[0]


def config(io, writes=(), reads=()):
    for b in KEY:
        io.outb(INDEX, b)
    try:
        io.outb(INDEX, 0x07)
        io.outb(INDEX + 1, 0x07)
        for reg, value in writes:
            io.outb(INDEX, reg)
            io.outb(INDEX + 1, value)
        out = []
        for reg in reads:
            io.outb(INDEX, reg)
            out.append(io.inb(INDEX + 1))
        return out
    finally:
        io.outb(INDEX, 0x02)
        io.outb(INDEX + 1, 0x02)


def read_disk(dev, seconds):
    p = subprocess.Popen(["dd", "if=" + dev, "of=/dev/null", "bs=1M",
                          "iflag=direct", "skip=%d" % (time.time() % 1000)],
                         stderr=subprocess.DEVNULL)
    time.sleep(seconds)
    p.terminate()
    p.wait()


def ask(text):
    return input("  %s Green LED blinked? [y/n] " % text).strip().lower()


def main():
    if os.geteuid() != 0:
        sys.exit("Run as root.")
    if subprocess.call(["systemctl", "-q", "is-active", "qnapx39d"]) == 0:
        sys.exit("Stop the plugin first: systemctl stop qnapx39d")
    bay = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    dev = "/dev/disk/by-path/" + BAYS[bay]
    if not os.path.exists(dev):
        sys.exit("No disk at %s" % dev)
    print("Bay %d = %s" % (bay, os.path.realpath(dev)))
    io = Port()
    hi, lo, f8, f9, fa, fb = config(io, reads=(0x62, 0x63, 0xF8, 0xF9,
                                               0xFA, 0xFB))
    base = hi << 8 | lo
    sets = {s: io.inb(base + s - 1) for s in (1, 2, 3, 5)}
    print("Blink1 loc 0x%02X ctl 0x%02X, blink2 loc 0x%02X ctl 0x%02X"
          % (f8, f9, fa, fb))
    print("GPIO sets: " + " ".join("%d=0x%02X" % kv for kv in sets.items()))
    results = []
    try:
        input("Look at bay %d and press Enter..." % bay)
        print("Step 1: as the BIOS left it, reading 8 s")
        read_disk(dev, 8)
        results.append(("BIOS state", ask("Step 1.")))
        config(io, [(0xF8, 0)])
        print("Step 2: blink1 unmapped (like the plugin), reading 8 s")
        read_disk(dev, 8)
        results.append(("blink1 unmapped", ask("Step 2.")))
        config(io, [(0xF8, f8), (0xF9, f9)])
        for s, bit in UNKNOWN:
            addr = base + s - 1
            io.outb(addr, sets[s] ^ 1 << bit)
            print("Step 3: GP%d%d flipped, reading 8 s" % (s, bit))
            read_disk(dev, 8)
            io.outb(addr, sets[s])
            results.append(("GP%d%d flipped" % (s, bit),
                            ask("GP%d%d." % (s, bit))))
    finally:
        for s, v in sets.items():
            io.outb(base + s - 1, v)
        config(io, [(0xF8, f8), (0xF9, f9), (0xFA, fa), (0xFB, fb)])
    print("\nRestored. Results:")
    for name, answer in results:
        print("  %-16s %s" % (name, answer or "-"))


if __name__ == "__main__":
    main()
