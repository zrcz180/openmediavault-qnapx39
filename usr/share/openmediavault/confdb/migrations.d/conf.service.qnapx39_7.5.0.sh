#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.5.0: front panel page settings for configs made by earlier versions.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
omv_config_exists "${xpath}/statusled" || \
	omv_config_add_key "${xpath}" "statusled" "1"
omv_config_exists "${xpath}/volumefull" || \
	omv_config_add_key "${xpath}" "volumefull" "95"
omv_config_exists "${xpath}/night" || \
	omv_config_add_key "${xpath}" "night" "0"
omv_config_exists "${xpath}/nightstart" || \
	omv_config_add_key "${xpath}" "nightstart" "22:00"
omv_config_exists "${xpath}/nightend" || \
	omv_config_add_key "${xpath}" "nightend" "07:00"
omv_config_exists "${xpath}/powerloss" || \
	omv_config_add_key "${xpath}" "powerloss" "bios"

exit 0
