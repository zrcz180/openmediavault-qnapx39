#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.2.0: front LCD settings for configs made by earlier versions.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
if ! omv_config_exists "${xpath}/lcd"; then
	omv_config_add_key "${xpath}" "lcd" "1"
fi
if ! omv_config_exists "${xpath}/lcdtimeout"; then
	omv_config_add_key "${xpath}" "lcdtimeout" "60"
fi

exit 0
