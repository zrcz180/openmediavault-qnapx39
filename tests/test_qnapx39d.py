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
            d.run(config(usedisk=False))
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
