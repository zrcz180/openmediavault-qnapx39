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
	implements \OMV\Engine\Notify\IListener, \OMV\Engine\Module\IServiceStatus
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
		return gettext("QNAP TS-x39 fan control.");
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

	public function bindListeners(\OMV\Engine\Notify\Dispatcher $dispatcher)
	{
		$dispatcher->addListener(OMV_NOTIFY_MODIFY,
			"org.openmediavault.conf.service.qnapx39", [$this, "setDirty"]);
	}
}
