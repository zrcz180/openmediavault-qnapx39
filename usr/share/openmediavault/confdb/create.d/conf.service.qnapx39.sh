#!/usr/bin/env dash
#
# This file is part of openmediavault-qnapx39.
#
# openmediavault-qnapx39 is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any
# later version. See the LICENSE file for details.

set -e

# Defaults live only in the datamodel (conf.service.qnapx39.json).
if ! omv-confdbadm exists "conf.service.qnapx39"; then
	omv-confdbadm read --defaults "conf.service.qnapx39" | \
		omv-confdbadm update "conf.service.qnapx39" -
fi

exit 0
