<?php
/**
 * This file is part of openmediavault-qnapx39.
 *
 * openmediavault-qnapx39 is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or any
 * later version. See the LICENSE file for details.
 */

class OMVRpcServiceQnapx39 extends \OMV\Rpc\ServiceAbstract
{
	const PWM_KEYS = ["manual", "min", "max"];

	public function getName()
	{
		return "Qnapx39";
	}

	public function initialize()
	{
		$this->registerMethod("getSettings");
		$this->registerMethod("setSettings");
		$this->registerMethod("getStatus");
		$this->registerMethod("getGauges");
		$this->registerMethod("getDisks");
		$this->registerMethod("getDevice");
		$this->registerMethod("setButtonSettings");
		$this->registerMethod("setFrontPanelSettings");
		$this->registerMethod("getProcessorMemory");
		$this->registerMethod("getTasks");
	}

	/**
	 * Settings with fan speeds as percent (the config uses PWM 0-255).
	 */
	public function getSettings($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$db = \OMV\Config\Database::getInstance();
		$result = $db->getAssoc("conf.service.qnapx39");
		foreach (self::PWM_KEYS as $key) {
			$result["{$key}speed"] = (int)round($result["{$key}pwm"] * 100 / 255);
			unset($result["{$key}pwm"]);
		}
		return $result;
	}

	public function setSettings($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$this->validateMethodParams($params, "rpc.qnapx39.setsettings");
		foreach (["cpu" => gettext("processor"), "sys" => gettext("system"),
				"disk" => gettext("disk")] as $prefix => $title) {
			if ($params["{$prefix}low"] >= $params["{$prefix}high"]) {
				throw new \OMV\Exception(sprintf(gettext(
					"The %s start temperature must be lower than the full speed temperature."),
					$title));
			}
		}
		if ($params["minspeed"] > $params["maxspeed"]) {
			throw new \OMV\Exception(gettext(
				"The lowest fan speed must not be greater than the highest fan speed."));
		}
		foreach (self::PWM_KEYS as $key) {
			$params["{$key}pwm"] = (int)round($params["{$key}speed"] * 255 / 100);
			unset($params["{$key}speed"]);
		}
		$db = \OMV\Config\Database::getInstance();
		$object = $db->get("conf.service.qnapx39");
		$object->setAssoc($params);
		$db->set($object);
		$result = $object->getAssoc();
		foreach (self::PWM_KEYS as $key) {
			$result["{$key}speed"] = (int)round($result["{$key}pwm"] * 100 / 255);
			unset($result["{$key}pwm"]);
		}
		return $result;
	}

	private function daemonStatus()
	{
		$cmd = new \OMV\System\Process("/usr/sbin/qnapx39d", "status");
		$output = [];
		try {
			$cmd->execute($output, $exitStatus);
		} catch (\Exception $e) {
			return [];
		}
		$status = json_decode(implode("\n", $output), true);
		return is_array($status) ? $status : [];
	}

	/**
	 * One row per reading for the Status page.
	 */
	public function getStatus($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$status = $this->daemonStatus();
		$rows = [];
		$rows[] = [
			"kind" => gettext("Fan control"),
			"label" => gettext("Daemon"),
			"value" => !empty($status["running"]) ?
				sprintf(gettext("Running, fan power %d %%"), $status["duty"]) :
				gettext("Not running"),
			"unit" => ""
		];
		if (!empty($status["running"])) {
			$problems = $status["problems"] ?? [];
			$rows[] = [
				"kind" => gettext("Status LED"),
				"label" => empty($problems) ? gettext("Green") : gettext("Red"),
				"value" => empty($problems) ? gettext("All well") :
					implode("; ", $problems),
				"unit" => ""
			];
		}
		if (!empty($status["running"])) {
			$storage = ["ok" => gettext("All good"),
				"degraded" => gettext("RAID degraded"),
				"rebuilding" => gettext("RAID rebuilding")];
			$rows[] = [
				"kind" => gettext("Storage"),
				"label" => gettext("Storage"),
				"value" => $storage[$status["storage"] ?? "ok"] ??
					$status["storage"],
				"unit" => ""
			];
		}
		foreach ($status["fans"] ?? [] as $fan) {
			$rows[] = [
				"kind" => gettext("Fan"),
				"label" => $fan["name"] . (!empty($fan["failed"]) ?
					" (" . gettext("failed?") . ")" : ""),
				"value" => $fan["rpm"] ?? "-",
				"unit" => "RPM"
			];
		}
		$kinds = ["cpu" => gettext("Processor"), "system" => gettext("System"),
			"disk" => gettext("Disk")];
		foreach ($kinds as $key => $kind) {
			foreach ($status["temps"][$key] ?? [] as $reading) {
				$rows[] = [
					"kind" => $kind,
					"label" => $reading[0],
					"value" => round($reading[1]),
					"unit" => "°C"
				];
			}
		}
		return $this->applyFilter($rows, 0, count($rows), null, null);
	}

	/**
	 * Dashboard gauges: hottest reading per source and the fan power.
	 */
	public function getGauges($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$status = $this->daemonStatus();
		// A missing key shows as "No reading" on the gauge.
		$result = [];
		foreach (["cpu", "system", "disk"] as $key) {
			$temps = array_column($status["temps"][$key] ?? [], 1);
			if (!empty($temps)) {
				$result[$key] = max($temps);
			}
		}
		if (isset($status["duty"])) {
			$result["duty"] = $status["duty"];
		}
		return empty($result) ? new \stdClass() : $result;
	}

	/**
	 * One row per bay for the Disks page.
	 */
	public function getDisks($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$status = $this->daemonStatus();
		$states = ["OK" => gettext("OK"), "FAILED" => gettext("Failed"),
			"sleep" => gettext("Standby"), "empty" => gettext("Empty")];
		$rows = [];
		foreach ($status["bays"] ?? [] as $bay) {
			$state = $bay["state"] ?? "empty";
			$rows[] = [
				"bay" => $bay["bay"],
				"device" => isset($bay["dev"]) ? "/dev/" . $bay["dev"] : "",
				"model" => $bay["model"] ?? "",
				"size" => $bay["size"] ?? "",
				"temp" => isset($bay["temp"]) ? round($bay["temp"]) . " °C" : "",
				"state" => $states[$state] ?? $state,
				"led" => ($state === "FAILED") ? gettext("Red") : gettext("Off")
			];
		}
		return $this->applyFilter($rows, 0, count($rows), null, null);
	}

	/**
	 * The installed version, from the first line of the package changelog.
	 */
	private function version()
	{
		$gz = @gzopen("/usr/share/doc/openmediavault-qnapx39/changelog.gz", "r");
		if ($gz === false) {
			return "";
		}
		$line = gzgets($gz, 200);
		gzclose($gz);
		return preg_match('/\(([^)]+)\)/', (string)$line, $m) ? $m[1] : "";
	}

	/**
	 * Device facts for the dashboard.
	 */
	public function getDevice($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$read = function($path) {
			$value = @file_get_contents($path);
			return ($value === false) ? "" : trim($value);
		};
		$cpu = "";
		if (preg_match('/^model name\s*:\s*(.+)$/m',
				$read("/proc/cpuinfo"), $m)) {
			$cpu = preg_replace('/\s+/', ' ', $m[1]);
		}
		$dmi = function($name) use ($read) {
			$value = $read("/sys/class/dmi/id/" . $name);
			// Placeholders BIOS vendors leave in empty DMI fields.
			return preg_match('/^(|none|default string|to be filled.*|' .
				'not specified|system (product name|serial number)|' .
				'0+|123456789)$/i', $value) ? "" : $value;
		};
		$board = trim($dmi("board_vendor") . " " . $dmi("board_name"));
		$model = trim($dmi("sys_vendor") . " " . $dmi("product_name"));
		$serial = $dmi("product_serial") ?: $dmi("board_serial");
		$bios = trim($dmi("bios_version") . ($dmi("bios_date") ?
			" (" . $dmi("bios_date") . ")" : ""));
		$status = $this->daemonStatus();
		$problems = $status["problems"] ?? [];
		$rows = [
			["property" => gettext("Model"), "value" => $model ?: $board],
			["property" => gettext("Serial number"), "value" => $serial],
			["property" => gettext("BIOS"), "value" => $bios],
			["property" => gettext("Host name"), "value" => gethostname()],
			["property" => gettext("Processor"), "value" => $cpu],
			["property" => gettext("Board"), "value" => $board],
			["property" => gettext("Kernel"), "value" => php_uname("r") .
				" (" . php_uname("m") . ")"],
			["property" => gettext("Plugin"), "value" => $this->version()],
			["property" => gettext("Hardware"), "value" =>
				empty($status["running"]) ? gettext("Service not running") :
				(empty($problems) ? gettext("All well") :
					implode("; ", $problems))]
		];
		return $this->applyFilter($rows, 0, count($rows), null, null);
	}

	/**
	 * Buttons page: only its own fields.
	 */
	public function setButtonSettings($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$this->validateMethodParams($params, "rpc.qnapx39.setbuttonsettings");
		$uuids = array_column($this->getTasks([], $context), "uuid");
		foreach (["usbcopytask", "resettask"] as $key) {
			if (!in_array($params[$key], $uuids, TRUE)) {
				throw new \OMV\Exception(gettext(
					"The selected scheduled task no longer exists."));
			}
		}
		$db = \OMV\Config\Database::getInstance();
		$object = $db->get("conf.service.qnapx39");
		$object->setAssoc($params);
		$db->set($object);
		return $object->getAssoc();
	}

	/**
	 * Scheduled Tasks a button can run, "None" first. qnapx39d runs the
	 * script OMV writes for the task, as the task's user.
	 */
	public function getTasks($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$db = \OMV\Config\Database::getInstance();
		$result = [["uuid" => "", "description" => gettext("None")]];
		foreach ($db->getByFilter("conf.system.cron.job", [
				"operator" => "stringEquals", "arg0" => "type",
				"arg1" => "userdefined"]) as $job) {
			$text = $job->get("comment") ?: $job->get("command");
			if (mb_strlen($text) > 60) {
				$text = mb_substr($text, 0, 57) . "...";
			}
			$result[] = [
				"uuid" => $job->get("uuid"),
				"description" => sprintf("%s (%s)", $text,
					$job->get("username"))
			];
		}
		return $result;
	}

	/**
	 * Front panel page: only its own fields.
	 */
	public function setFrontPanelSettings($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$this->validateMethodParams($params, "rpc.qnapx39.setfrontpanelsettings");
		$db = \OMV\Config\Database::getInstance();
		$object = $db->get("conf.service.qnapx39");
		$object->setAssoc($params);
		$db->set($object);
		return $object->getAssoc();
	}

	private static function formatSize($mb)
	{
		return ($mb >= 1024) ? sprintf("%s GB", round($mb / 1024, 1)) :
			sprintf("%d MB", $mb);
	}

	/**
	 * System page, Processor & memory tab: /proc/cpuinfo, cpufreq and
	 * dmidecode (memory array and devices).
	 */
	public function getProcessorMemory($params, $context)
	{
		$this->validateMethodContext($context, ["role" => OMV_ROLE_ADMINISTRATOR]);
		$rows = [];
		$add = function($property, $value) use (&$rows) {
			if ($value !== null && $value !== "") {
				$rows[] = ["property" => $property, "value" => $value];
			}
		};
		$cpuinfo = (string)@file_get_contents("/proc/cpuinfo");
		if (preg_match('/^model name\s*:\s*(.+)$/m', $cpuinfo, $m)) {
			$add(gettext("Processor"), preg_replace('/\s+/', ' ', $m[1]));
		}
		$threads = preg_match_all('/^processor\s*:/m', $cpuinfo);
		$cores = preg_match('/^cpu cores\s*:\s*(\d+)/m', $cpuinfo, $m) ?
			(int)$m[1] : $threads;
		if ($cores) {
			$add(gettext("Cores"), ($threads > $cores) ?
				sprintf(gettext("%d cores, %d threads"), $cores, $threads) :
				sprintf(gettext("%d cores"), $cores));
		}
		$add(gettext("Architecture"), php_uname("m") .
			(preg_match('/^flags\s*:.*\blm\b/m', $cpuinfo) ?
				" (" . gettext("the CPU can run 64-bit") . ")" :
				" (" . gettext("32-bit CPU") . ")"));
		$freq = "/sys/devices/system/cpu/cpu0/cpufreq/";
		$min = (int)@file_get_contents($freq . "cpuinfo_min_freq");
		$max = (int)@file_get_contents($freq . "cpuinfo_max_freq");
		if ($min && $max) {
			$add(gettext("Clock speed"), sprintf(gettext("%s to %s GHz"),
				round($min / 1e6, 1), round($max / 1e6, 1)));
		} elseif (preg_match('/^cpu MHz\s*:\s*([\d.]+)/m', $cpuinfo, $m)) {
			$add(gettext("Clock speed"), sprintf(gettext("%s GHz"),
				round($m[1] / 1000, 2)));
		}
		$output = [];
		try {
			$cmd = new \OMV\System\Process("dmidecode", "-t", "memory");
			$cmd->execute($output, $exitStatus);
		} catch (\Exception $e) {
			$output = [];
		}
		$maxMb = null; $ecc = null; $modules = []; $cur = null;
		foreach ($output as $line) {
			$line = trim($line);
			if ($line === "Memory Device") {
				if ($cur !== null) { $modules[] = $cur; }
				$cur = [];
				continue;
			}
			if (!preg_match('/^([^:]+):\s*(.*)$/', $line, $m)) {
				continue;
			}
			list(, $key, $value) = $m;
			if ($cur === null) {
				if ($key === "Maximum Capacity" &&
						preg_match('/(\d+)\s*(MB|GB)/', $value, $v)) {
					$maxMb = $v[1] * ($v[2] === "GB" ? 1024 : 1);
				}
				if ($key === "Error Correction Type") {
					$ecc = !preg_match('/^None$/i', $value);
				}
				continue;
			}
			$cur[$key] = $value;
		}
		if ($cur !== null) { $modules[] = $cur; }
		$used = 0; $total = 0; $slots = [];
		foreach ($modules as $mod) {
			$size = 0;
			if (preg_match('/(\d+)\s*(MB|GB)/', $mod["Size"] ?? "", $v)) {
				$size = $v[1] * ($v[2] === "GB" ? 1024 : 1);
			}
			if ($size) {
				$used++;
				$total += $size;
				$speed = preg_match('/(\d+)/', $mod["Speed"] ?? "", $v) ?
					sprintf(gettext("%d MT/s"), $v[1]) : null;
				$maker = implode(" ", array_filter(array_map(function($k) use ($mod) {
					$x = trim($mod[$k] ?? "");
					return preg_match('/^(unknown|not specified|' .
						'manufacturer\d*|partnum\d*|0+)$/i', $x) ? "" : $x;
				}, ["Manufacturer", "Part Number"])));
				$value = implode(" ", array_filter([self::formatSize($size),
					$mod["Type"] ?? null, $speed]));
				if ($maker !== "") {
					$value .= ", " . $maker;
				}
			} else {
				$value = gettext("Empty");
			}
			$slots[] = $value;
		}
		if ($used) {
			$add(gettext("Memory"), sprintf(gettext("%s installed, %d of %d slots used"),
				self::formatSize($total), $used, count($modules)));
		} elseif (preg_match('/^MemTotal:\s*(\d+)/m',
				(string)@file_get_contents("/proc/meminfo"), $m)) {
			$add(gettext("Memory"), self::formatSize((int)($m[1] / 1024)));
		}
		if ($maxMb) {
			$add(gettext("Maximum memory (BIOS)"), self::formatSize($maxMb));
		}
		if ($ecc !== null) {
			$add(gettext("Error correction (ECC)"), $ecc ? gettext("Yes") :
				gettext("No"));
		}
		foreach ($slots as $n => $value) {
			$add(sprintf(gettext("Memory slot %d"), $n + 1), $value);
		}
		return $this->applyFilter($rows, 0, count($rows), null, null);
	}
}
