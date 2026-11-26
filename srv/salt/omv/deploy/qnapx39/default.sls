# This file is part of openmediavault-qnapx39.
#
# openmediavault-qnapx39 is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any
# later version. See the LICENSE file for details.

{% set config = salt['omv_conf.get']('conf.service.qnapx39') %}

# The IT8718F is driven by the in-kernel it87 driver; Debian does not load
# it on its own.
{% if config.loadmodule | to_bool %}

configure_qnapx39_modules_load:
  file.managed:
    - name: "/etc/modules-load.d/openmediavault-qnapx39.conf"
    - contents: |
        {{ pillar['headers']['auto_generated'] }}
        {{ pillar['headers']['warning'] }}
        it87
    - user: root
    - group: root
    - mode: '0644'

load_qnapx39_it87:
  cmd.run:
    - name: "modprobe it87"
    - unless: "test -d /sys/module/it87"

{% else %}

remove_qnapx39_modules_load:
  file.absent:
    - name: "/etc/modules-load.d/openmediavault-qnapx39.conf"

{% endif %}

configure_qnapx39d:
  file.serialize:
    - name: "/etc/qnapx39d/qnapx39d.json"
    - dataset:
        enable: {{ config.enable | to_bool | json }}
        interval: {{ config.interval }}
        fanmode: {{ config.fanmode | json }}
        manualpwm: {{ config.manualpwm }}
        minpwm: {{ config.minpwm }}
        maxpwm: {{ config.maxpwm }}
        hysteresis: {{ config.hysteresis }}
        usecpu: {{ config.usecpu | to_bool | json }}
        cpulow: {{ config.cpulow }}
        cpuhigh: {{ config.cpuhigh }}
        usesystem: {{ config.usesystem | to_bool | json }}
        syslow: {{ config.syslow }}
        syshigh: {{ config.syshigh }}
        systemsensors: {{ config.systemsensors | json }}
        usedisk: {{ config.usedisk | to_bool | json }}
        disklow: {{ config.disklow }}
        diskhigh: {{ config.diskhigh }}
        diskinterval: {{ config.diskinterval }}
        fans: {{ config.fans | json }}
        leds: {{ config.leds | to_bool | json }}
        bays: {{ config.bays | json }}
        lcd: {{ config.lcd | to_bool | json }}
        lcdtimeout: {{ config.lcdtimeout }}
        lcdpower: {{ config.lcdpower | to_bool | json }}
    - serializer: json
    - makedirs: True
    - user: root
    - group: root
    - mode: '0644'

{% if config.enable | to_bool %}

start_qnapx39d_service:
  service.running:
    - name: qnapx39d
    - enable: True
    - watch:
      - file: configure_qnapx39d

{% else %}

stop_qnapx39d_service:
  service.dead:
    - name: qnapx39d
    - enable: False

{% endif %}
