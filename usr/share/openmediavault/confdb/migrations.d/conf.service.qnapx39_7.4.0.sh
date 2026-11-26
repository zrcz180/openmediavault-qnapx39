#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.4.0: button and beep settings for configs made by earlier versions.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
if ! omv_config_exists "${xpath}/beep"; then
	omv_config_add_key "${xpath}" "beep" "0"
fi
for key in usbcopytask resettask; do
	if ! omv_config_exists "${xpath}/${key}"; then
		omv_config_add_key "${xpath}" "${key}" ""
	fi
done

exit 0
