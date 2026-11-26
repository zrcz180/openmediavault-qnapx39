"""Tests for qnapx39d against a fake sysfs tree. Run: make test"""
import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "usr", "sbin", "qnapx39d")
loader = importlib.machinery.SourceFileLoader("qnapx39d", PATH)
spec = importlib.util.spec_from_loader("qnapx39d", loader)
d = importlib.util.module_from_spec(spec)
loader.exec_module(d)
# Never touch real I/O ports from the tests.
d.PORT_DEVICE = "/nonexistent/port"


def config(**kw):
    c = dict(d.DEFAULTS)
    c.update(kw)
    with tempfile.NamedTemporaryFile("w", suffix=".json",
                                     delete=False) as f:
        json.dump(c, f)
    try:
        return d.load_config(f.name)
    finally:
        os.unlink(f.name)


class FakeSysfs(unittest.TestCase):
    """A TS-639 Pro as Rui's NAS reports it: coretemp + it8718."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d.SYSFS = self.tmp.name
        self.core = self.hwmon(0, "coretemp", {"temp2_input": "28000",
                                               "temp2_label": "Core 0"})
        self.sio = self.hwmon(1, "it8718", {
            "temp1_input": "40000", "temp2_input": "38000",
            "temp3_input": "33000", "fan1_input": "1717",
            "fan2_input": "1713", "fan3_input": "0",
            "pwm1": "128", "pwm2": "128", "pwm3": "128",
            "pwm1_enable": "1", "pwm2_enable": "1", "pwm3_enable": "1"})

    def tearDown(self):
        self.tmp.cleanup()

    def hwmon(self, n, name, files):
        path = os.path.join(self.tmp.name, "class", "hwmon", "hwmon%d" % n)
        os.makedirs(path)
        files = dict(files, name=name)
        for k, v in files.items():
            with open(os.path.join(path, k), "w") as f:
                f.write(v + "\n")
        return path

    def value(self, name):
        with open(os.path.join(self.sio, name)) as f:
            return f.read().strip()

    def test_finds_chip_and_reads(self):
        sio = d.SuperIO.find()
        self.assertEqual(sio.name, "it8718")
        self.assertEqual(sio.temps(["temp1", "temp2", "temp3"]),
                         [("temp1", 40.0), ("temp2", 38.0), ("temp3", 33.0)])
        self.assertEqual(sio.rpm(1), 1717)
        self.assertEqual(d.cpu_temps(), [("Core 0", 28.0)])

    def test_set_pwm_switches_to_manual(self):
        with open(os.path.join(self.sio, "pwm2_enable"), "w") as f:
            f.write("2")
        self.assertEqual(d.SuperIO.find().set_pwm(2, 300), 255)
        self.assertEqual(self.value("pwm2_enable"), "1")

    def test_failsafe_sets_full_speed_on_configured_fans_only(self):
        d.failsafe(config())
        self.assertEqual(self.value("pwm1"), "255")
        self.assertEqual(self.value("pwm2"), "255")
        self.assertEqual(self.value("pwm3"), "128")

    def test_implausible_sensor_ignored(self):
        with open(os.path.join(self.sio, "temp3_input"), "w") as f:
            f.write("-128000")
        self.assertEqual(len(d.SuperIO.find().temps(["temp3"])), 0)

    def test_run_one_poll_then_failsafe(self):
        d.STATUS_FILE = os.path.join(self.tmp.name, "run", "status.json")
        polls = []

        def sleep(seconds):
            with open(d.STATUS_FILE) as f:
                polls.append(json.load(f))
            raise d.Stop()

        real_sleep, d.time.sleep = d.time.sleep, sleep
        try:
            d.run(config(usedisk=False, leds=False, lcd=False))
        finally:
            d.time.sleep = real_sleep
        # Board at 40 C is below 45 C and CPU 28 C: lowest speed.
        self.assertEqual(polls[0]["pwm"], 77)
        self.assertEqual(polls[0]["duty"], 30)
        # Stopping leaves the fans at full speed.
        self.assertEqual(self.value("pwm1"), "255")
        self.assertEqual(self.value("pwm2"), "255")

    def test_live_status_without_daemon(self):
        d.STATUS_FILE = os.path.join(self.tmp.name, "none.json")
        st = d.status(config())
        self.assertFalse(st["running"])
        self.assertEqual([f["rpm"] for f in st["fans"]], [1717, 1713])


class Curve(unittest.TestCase):
    def setUp(self):
        self.c = config(minpwm=77, maxpwm=255, hysteresis=3)

    def test_linear(self):
        self.assertEqual(d.curve(40, 45, 60, 77, 255), 77)
        self.assertEqual(d.curve(60, 45, 60, 77, 255), 255)
        self.assertEqual(d.curve(52.5, 45, 60, 77, 255), 166)

    def test_no_readings_is_full_speed(self):
        self.assertEqual(d.target_pwm(self.c, [], 100), 255)

    def test_critical_is_full_speed(self):
        self.assertEqual(
            d.target_pwm(self.c, [("sys", 71, 45, 60)], 100), 255)

    def test_hottest_source_wins(self):
        srcs = d.sources(self.c, [("c", 50)], [("temp1", 52.5)], [])
        self.assertEqual(d.target_pwm(self.c, srcs, None), 166)

    def test_disabled_source_ignored(self):
        c = config(usesystem=False)
        srcs = d.sources(c, [("c", 50)], [("temp1", 59)], [])
        self.assertEqual([s[0] for s in srcs], ["cpu"])

    def test_rises_at_once_falls_with_hysteresis(self):
        srcs = [("sys", 52.5, 45, 60)]
        self.assertEqual(d.target_pwm(self.c, srcs, 100), 166)
        # 1 degree cooler: within hysteresis, keep 166.
        self.assertEqual(
            d.target_pwm(self.c, [("sys", 51.5, 45, 60)], 166), 166)
        # 5 degrees cooler: falls, but only to the hysteresis point.
        self.assertEqual(
            d.target_pwm(self.c, [("sys", 47.5, 45, 60)], 166),
            d.curve(50.5, 45, 60, 77, 255))

    def test_manual(self):
        c = config(fanmode="manual", manualpwm=200)
        self.assertEqual(d.target_pwm(c, [], None), 200)

    def test_config_lists(self):
        c = config(fans="1, 2", systemsensors="temp1,temp3")
        self.assertEqual(c["fans"], [1, 2])
        self.assertEqual(c["systemsensors"], ["temp1", "temp3"])


class FakeIO:
    """I/O ports: Simple I/O sets at 0xA20.. and a config space."""

    def __init__(self, values):
        self.ports = {0xA20 + i: v for i, v in enumerate(values)}
        self.config = {}
        self.index = None

    def outb(self, addr, value):
        if addr == 0x2E:
            self.index = value
        elif addr == 0x2F:
            self.config[self.index] = value
        else:
            self.ports[addr] = value

    def inb(self, addr):
        if addr == 0x2F:
            return self.config.get(self.index, 0)
        return self.ports[addr]


class Leds(unittest.TestCase):
    # Values from the TS-639 Pro dump: set 2 = 0x0F, set 3 = 0x9F.
    def setUp(self):
        self.io = FakeIO([0xED, 0x0F, 0x9F, 0x7B, 0xFD])
        self.cfg = d.SuperIOConfig(self.io)
        # BIOS blinks GP26 (location 0x16) on blink generator 1.
        self.panel = d.FrontPanel(self.io, 0xA20, [0x16, 0], self.cfg)

    def pin(self, s, bit):
        return self.io.ports[0xA20 + s - 1] >> bit & 1

    def test_all_well_is_green_and_stops_blinking(self):
        self.panel.show(True, set())
        self.assertEqual(self.pin(3, 5), 0)   # green on (active-low)
        self.assertEqual(self.pin(3, 4), 1)   # red off
        self.assertEqual(self.io.config[0xF8], 0)
        self.assertEqual(self.io.ports[0xA21] & 0x0F, 0x0F)  # disks 1-4 off

    def test_problem_is_red_and_failed_bay_lights(self):
        self.panel.show(False, {1, 6})
        self.assertEqual(self.pin(3, 5), 1)
        self.assertEqual(self.pin(3, 4), 0)
        self.assertEqual(self.pin(2, 3), 0)   # bay 1 = GP23
        self.assertEqual(self.pin(3, 0), 0)   # bay 6 = GP30
        self.assertEqual(self.pin(2, 2), 1)

    def test_blink_unmapped_once(self):
        self.panel.show(True, set())
        self.io.config[0xF8] = 0x16  # if something maps it again
        self.panel.show(True, set())
        self.assertEqual(self.io.config[0xF8], 0x16)

    def test_usb_led(self):
        self.panel.show(True, set(), usb=True)
        self.assertEqual(self.pin(5, 0), 0)   # GP50 on
        self.assertEqual(self.io.ports[0xA24] | 1, 0xFD | 1)
        self.panel.show(True, set(), usb=False)
        self.assertEqual(self.pin(5, 0), 1)

    def test_other_pins_untouched_and_restore(self):
        self.panel.show(False, {1, 2, 3, 4, 5, 6}, usb=True)
        self.assertEqual(self.io.ports[0xA22] & 0x0C, 0x9F & 0x0C)  # GP32/33
        self.assertEqual(self.io.ports[0xA20], 0xED)
        self.panel.restore()
        self.assertEqual(self.io.ports[0xA21], 0x0F)
        self.assertEqual(self.io.ports[0xA22], 0x9F)
        self.assertEqual(self.io.ports[0xA24], 0xFD)
        self.assertEqual(self.io.config[0xF8], 0x16)

    def test_panel_state(self):
        class Disks:
            failed = {"sdb"}
        mdstat = "md0 : active raid5 sdc1[2](F) sdb1[1] sda1[0]\n" \
                 "      5860 blocks [3/2] [UU_]\n"
        ok, bays, problems = d.panel_state(
            [{"name": "fan1", "failed": False}], Disks(), mdstat,
            {1: "sda", 2: "sdb", 3: "sdc"})
        self.assertFalse(ok)
        self.assertEqual(bays, {2, 3})
        self.assertIn("RAID degraded", problems)
        ok, bays, problems = d.panel_state([], type("D", (), {"failed": set()}),
                                           "md0 : active raid1 [2/2] [UU]", {})
        self.assertTrue(ok)

    def test_smart_health(self):
        self.assertFalse(d.parse_smart_health({"smart_status": {"passed": False}}))
        self.assertIsNone(d.parse_smart_health({}))


class Collectd(unittest.TestCase):
    def test_values(self):
        st = {"duty": 30, "fans": [{"name": "fan1", "rpm": 1200}],
              "temps": {"cpu": [["Core 0", 28.0]],
                        "system": [["temp1", 40.0], ["temp2", 38.0]],
                        "disk": []}}
        self.assertEqual(d.collectd_values(st), [
            ("temperature-cpu", 28.0), ("temperature-system", 40.0),
            ("fanspeed-fan1", 1200), ("percent-duty", 30)])

    def test_smart_temp(self):
        self.assertEqual(d.parse_smart_temp({"temperature":
                                             {"current": 36}}), 36.0)
        self.assertIsNone(d.parse_smart_temp({}))


if __name__ == "__main__":
    unittest.main()


class FrontLcd(unittest.TestCase):
    def setUp(self):
        self.r, self.w = os.pipe()
        self.io = FakeIO([0xED, 0x0F, 0x9F, 0x7B, 0xFD])
        self.lcd = d.Lcd(self.w, self.io, 0xA20)
        self.now = [0.0]
        d.time.sleep, self.real_sleep = (lambda s: None), d.time.sleep

    def tearDown(self):
        d.time.sleep = self.real_sleep
        os.close(self.r)
        try:
            os.close(self.w)
        except OSError:
            pass

    def sent(self):
        os.set_blocking(self.r, False)
        try:
            return os.read(self.r, 4096)
        except BlockingIOError:
            return b""

    def test_parse_buttons(self):
        self.assertEqual(d.parse_buttons(b"\x53\x05\x00\x01\x53\x05\x00\x00"),
                         ([1], b""))
        self.assertEqual(d.parse_buttons(b"xx\x53\x05\x00\x02\x53\x05"),
                         ([2], b"\x53\x05"))
        self.assertEqual(d.parse_buttons(b"\x53\x05\x00"), ([], b"\x53\x05\x00"))
        self.assertEqual(d.parse_buttons(b"junk"), ([], b""))

    def test_power_backlight_and_lines(self):
        self.lcd.power(True)
        self.assertEqual(self.io.ports[0xA20] & 1, 0)   # GP10 low: on
        self.lcd.backlight(True)
        self.lcd.backlight(True)                         # sent once
        self.lcd.show(("nas", "10.0.0.2"))
        self.lcd.show(("nas", "10.0.0.3"))               # only line 2
        self.assertEqual(
            self.sent(),
            b"\x4d\x5e\x01"
            b"\x4d\x0c\x00\x20nas             "
            b"\x4d\x0c\x01\x2010.0.0.2        "
            b"\x4d\x0c\x01\x2010.0.0.3        ")
        self.lcd.close(("bye", ""))
        self.assertEqual(self.io.ports[0xA20], 0xED)    # GP10 back to 1

    def test_text_is_ascii_16(self):
        self.assertEqual(d.lcd_text("Temperatura 40°C!!"), "Temperatura 40?C")

    def test_pages(self):
        st = {"duty": 30, "problems": [],
              "fans": [{"name": "fan1", "rpm": 1715}, {"name": "fan2",
                                                       "rpm": 1713}],
              "temps": {"cpu": [("Core 0", 28.0)],
                        "system": [("temp1", 40.0), ("temp2", 38.0)],
                        "disk": [("sdb", 35.0), ("sdc", 38.0)]},
              "bays": [{"bay": 1, "dev": "sdh", "model": "WDC WD20EFRX-68",
                        "size": "2.0T", "temp": 35.0, "state": "OK"},
                       {"bay": 2, "dev": "sdb", "model": "ST4000", "size":
                        "4.0T", "temp": None, "state": "FAILED"},
                       {"bay": 3, "dev": None, "state": "empty"}]}
        nics = [("eth0", "192.168.1.5", "1000Mb"), ("eth1", None, "down")]
        pages = d.lcd_pages(st, "nas", nics, ("Up 1d 02:03", "L"), True)
        self.assertEqual(pages, [
            ("nas eth0 1000Mb", "192.168.1.5"),
            ("nas eth1 down", "no IP address"),
            ("Status: OK", "All well"),
            ("CPU 28C", "System 40C"), ("Fans 30%", "1715 1713 RPM"),
            ("Disks 2, max 38C", "min 35C"),
            ("B1 sdh 35C OK", "2.0T WDC WD20EFRX-68"),
            ("B2 sdb  FAIL", "4.0T ST4000"),
            ("Bay 3", "empty"),
            ("Up 1d 02:03", "L"), d.POWER_PAGE])
        pages = d.lcd_pages({"problems": ["fan1 failed"]}, "nas", [])
        self.assertEqual(pages[0], ("nas", "no network"))
        self.assertEqual(pages[1], ("Status: PROBLEM", "fan1 failed"))
        self.assertNotIn(d.POWER_PAGE, pages)

    def panel(self, **kw):
        self.ran = []
        panel = d.LcdPanel(self.lcd, 60, clock=lambda: self.now[0],
                           runner=self.ran.append, **kw)
        panel.interfaces_time = 1e9   # no real network lookups
        panel.interfaces = [("eth0", "10.0.0.2", "1000Mb")]
        return panel

    def test_buttons_pages_and_backlight_timeout(self):
        panel = self.panel()
        panel.update({"problems": []})
        panel.refresh()
        self.assertEqual(panel.page, 0)
        self.assertTrue(self.lcd.lit)
        panel.press(d.LCD_SELECT)
        panel.refresh()
        self.assertEqual(panel.page, 1)
        panel.press(d.LCD_ENTER)
        panel.press(d.LCD_ENTER)
        panel.refresh()
        self.assertEqual(panel.page, len(panel.pages()) - 1)
        self.now[0] = 59.0
        panel.refresh()
        self.assertTrue(self.lcd.lit)
        self.now[0] = 61.0
        panel.refresh()
        self.assertFalse(self.lcd.lit)
        page = panel.page
        panel.press(d.LCD_SELECT)        # first press only wakes
        panel.refresh()
        self.assertTrue(self.lcd.lit)
        self.assertEqual(panel.page, page)
        # A new problem jumps to the Status page and lights the panel.
        self.now[0] = 200.0
        panel.refresh()
        self.assertFalse(self.lcd.lit)
        panel.update({"problems": ["RAID degraded"]})
        panel.refresh()
        self.assertTrue(self.lcd.lit)
        self.assertEqual(panel.page, 1)
        self.assertEqual(self.lcd.lines[1], d.lcd_text("RAID degraded"))

    def go_to_power_menu(self, panel):
        panel.refresh()
        panel.press(d.LCD_ENTER)          # back from page 0: last page
        panel.refresh()
        self.assertEqual(self.lcd.lines[0], d.lcd_text(d.POWER_PAGE[0]))
        panel.press(d.LCD_ENTER)          # open the menu
        panel.refresh()
        self.assertEqual(self.lcd.lines[0], d.lcd_text("> Cancel"))

    def test_reboot_needs_two_enters(self):
        panel = self.panel(power=True)
        self.go_to_power_menu(panel)
        panel.press(d.LCD_SELECT)         # Reboot
        panel.press(d.LCD_ENTER)
        panel.refresh()
        self.assertEqual(self.lcd.lines[0], d.lcd_text("Reboot? Sure?"))
        self.assertEqual(self.ran, [])
        panel.press(d.LCD_ENTER)
        panel.refresh()
        self.assertEqual(self.ran, [["systemctl", "reboot"]])
        self.assertEqual(self.lcd.lines[0], d.lcd_text("Rebooting..."))
        panel.press(d.LCD_SELECT)         # ignored from now on
        self.assertEqual(len(self.ran), 1)

    def test_menu_cancels(self):
        panel = self.panel(power=True)
        self.go_to_power_menu(panel)
        panel.press(d.LCD_SELECT)
        panel.press(d.LCD_SELECT)         # Shut down
        panel.press(d.LCD_ENTER)
        panel.press(d.LCD_SELECT)         # "no"
        panel.refresh()
        self.assertIsNone(panel.menu)
        self.assertEqual(self.lcd.lines[0], d.lcd_text(d.POWER_PAGE[0]))
        panel.press(d.LCD_ENTER)          # menu again
        panel.press(d.LCD_SELECT)
        panel.press(d.LCD_ENTER)          # Sure?
        self.now[0] = 16.0                # no answer: cancelled
        panel.refresh()
        self.assertIsNone(panel.menu)
        panel.press(d.LCD_ENTER)
        self.assertEqual(self.ran, [])

    def test_no_power_page_without_option(self):
        panel = self.panel()
        self.assertNotIn(d.POWER_PAGE, panel.pages())


class Bays(FakeSysfs):
    def disk(self, dev, port, model, sectors):
        path = os.path.join(self.tmp.name, "devices", "pci0", port,
                            "host0", "block", dev)
        os.makedirs(os.path.join(path, "device"))
        with open(os.path.join(path, "device", "model"), "w") as f:
            f.write(model + "\n")
        with open(os.path.join(path, "size"), "w") as f:
            f.write("%d\n" % sectors)
        block = os.path.join(self.tmp.name, "block")
        os.makedirs(block, exist_ok=True)
        os.symlink(path, os.path.join(block, dev))

    def test_bay_info(self):
        self.disk("sdh", "ata13", "WDC WD20EFRX-68EUZN0  ", 3907029168)
        self.disk("sdb", "ata2", "ST500DM002", 976773168)
        info = d.bay_info(["ata13", "ata2", "ata3"], [("sdh", 34.0)],
                          {"sdb"}, set())
        self.assertEqual(info, [
            {"bay": 1, "dev": "sdh", "model": "WDC WD20EFRX-68EUZN0",
             "size": "2.0T", "temp": 34.0, "state": "OK"},
            {"bay": 2, "dev": "sdb", "model": "ST500DM002", "size": "500G",
             "temp": None, "state": "sleep"},
            {"bay": 3, "dev": None, "state": "empty"}])
        self.assertEqual(d.bay_info(["ata13"], [], set(), {1})[0]["state"],
                         "FAILED")

    def test_network_interfaces(self):
        net = os.path.join(self.tmp.name, "class", "net")
        for name, files in (("lo", {}),
                            ("eth0", {"device": "", "operstate": "up",
                                      "speed": "1000"}),
                            ("eth1", {"device": "", "operstate": "down",
                                      "speed": "-1"}),
                            ("eth2", {"device": "", "master": "",
                                      "operstate": "up"}),
                            ("docker0", {"operstate": "down"})):
            os.makedirs(os.path.join(net, name))
            for k, v in files.items():
                with open(os.path.join(net, name, k), "w") as f:
                    f.write(v)
        real, d.ipv4_address = d.ipv4_address, \
            {"eth0": "192.168.1.5"}.get
        try:
            self.assertEqual(d.network_interfaces(), [
                ("eth0", "192.168.1.5", "1000Mb"), ("eth1", None, "down")])
        finally:
            d.ipv4_address = real
