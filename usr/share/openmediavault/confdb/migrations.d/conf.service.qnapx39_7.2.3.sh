#!/bin/sh
#
# This file is part of openmediavault-qnapx39 (GPL-3.0-or-later).
#
# 7.2.3: bays by stable SATA port name. The old default listed kernel
# ataN numbers, which change between boots; replace it if still in use.

set -e

. /usr/share/openmediavault/scripts/helper-functions

xpath="/config/services/qnapx39/bays"
if [ "$(omv_config_get "${xpath}")" = "ata13,ata2,ata3,ata4,ata9,ata10" ]; then
	omv_config_update "${xpath}" "pci-0000:00:1f.1-ata-1,pci-0000:03:00.0-ata-2,pci-0000:03:00.0-ata-3,pci-0000:03:00.0-ata-4,pci-0000:04:00.0-ata-1,pci-0000:04:00.0-ata-2"
fi

exit 0
