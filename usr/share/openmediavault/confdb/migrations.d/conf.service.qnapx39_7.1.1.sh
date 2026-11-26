#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.1.1: front panel LED settings for configs made by 7.0.0 or 7.1.0.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
if ! omv_config_exists "${xpath}/leds"; then
	omv_config_add_key "${xpath}" "leds" "1"
fi
if ! omv_config_exists "${xpath}/bays"; then
	omv_config_add_key "${xpath}" "bays" "ata13,ata2,ata3,ata4,ata9,ata10"
fi

exit 0
