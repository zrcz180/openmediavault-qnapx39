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
}
