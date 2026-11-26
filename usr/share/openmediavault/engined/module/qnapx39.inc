<?php
/**
 * This file is part of openmediavault-qnapx39.
 *
 * openmediavault-qnapx39 is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as published
 * by the Free Software Foundation, either version 3 of the License, or any
 * later version. See the LICENSE file for details.
 */

class OMVModuleQnapx39 extends \OMV\Engine\Module\ServiceAbstract
	implements \OMV\Engine\Notify\IListener, \OMV\Engine\Module\IServiceStatus,
		\OMV\Engine\Module\INotification
{
	/**
	 * Must match the salt state directory srv/salt/omv/deploy/qnapx39.
	 */
	public function getName()
	{
		return "qnapx39";
	}

	public function getDescription()
	{
		return gettext("QNAP TS-x39 fans, LEDs, LCD and fault emails.");
	}

	public function getStatus()
	{
		$db = \OMV\Config\Database::getInstance();
		$object = $db->get("conf.service.qnapx39");
		$systemCtl = new \OMV\System\SystemCtl("qnapx39d");
		return [
			"name" => $this->getName(),
			"title" => gettext("QNAP fan control"),
			"enabled" => $object->get("enable"),
			"running" => $systemCtl->isActive()
		];
	}

	/**
	 * System > Notification > Events entry. qnapx39d mails root (forwarded
	 * to the configured address) only while this and email are enabled.
	 */
	public function getNotificationConfig()
	{
		return [[
			"id" => "qnapx39",
			"type" => gettext("Hardware"),
			"title" => gettext("QNAP TS-x39 hardware (fans, temperatures, disks, RAID, volumes)")
		]];
	}

	public function bindListeners(\OMV\Engine\Notify\Dispatcher $dispatcher)
	{
		$dispatcher->addListener(OMV_NOTIFY_MODIFY,
			"org.openmediavault.conf.service.qnapx39", [$this, "setDirty"]);
		// The notify flag in qnapx39d.json follows the notification settings.
		$dispatcher->addListener(OMV_NOTIFY_MODIFY,
			"org.openmediavault.conf.system.notification.email",
			[$this, "setDirty"]);
		$dispatcher->addListener(OMV_NOTIFY_MODIFY,
			"org.openmediavault.conf.system.notification.notification",
			[$this, "setDirty"]);
	}
}
