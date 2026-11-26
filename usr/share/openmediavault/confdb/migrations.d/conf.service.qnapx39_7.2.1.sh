#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.2.1: LCD reboot/shutdown setting for configs made by earlier versions.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
if ! omv_config_exists "${xpath}/lcdpower"; then
	omv_config_add_key "${xpath}" "lcdpower" "1"
fi

exit 0
