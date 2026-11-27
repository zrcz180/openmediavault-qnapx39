#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.5.1: blink the green bay lights on disk activity.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39"
omv_config_exists "${xpath}/activityblink" || \
	omv_config_add_key "${xpath}" "activityblink" "1"

exit 0
