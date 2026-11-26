# This file is part of openmediavault-qnapx39.
#
# openmediavault-qnapx39 is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any
# later version. See the LICENSE file for details.

# Graphs: "qnapx39d collectd" only reads the daemon's status file, so it
# never touches the hardware or wakes sleeping disks.
configure_collectd_conf_qnapx39_plugin:
  file.managed:
    - name: "/etc/collectd/collectd.conf.d/qnapx39.conf"
    - contents: |
        LoadPlugin exec
        <Plugin exec>
            Exec "nobody" "/usr/sbin/qnapx39d" "collectd"
        </Plugin>
    - user: root
    - group: root
    - mode: '0644'
