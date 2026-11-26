# This file is part of openmediavault-qnapx39.
#
# openmediavault-qnapx39 is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or any
# later version. See the LICENSE file for details.
#
# Adapted from openmediavault-qnap (GPL-3.0-or-later).
"""Graphs for the values `qnapx39d collectd` feeds to collectd."""
import glob
import os

import openmediavault.mkrrdgraph

COLORS = ['#ff1300', '#0bb6ff', '#00df00', '#fdaf00', '#9b59b6', '#1abc9c']

LABELS = {'cpu': 'CPU', 'system': 'Board', 'disk': 'Hard disks',
          'duty': 'Fans'}

# (graph, collectd type, title, vertical label, GPRINT unit)
GRAPHS = [
    ('temperature', 'temperature', 'Temperatures (hottest per source)',
     'Celsius', 'C'),
    ('fanspeed', 'fanspeed', 'Fan speed', 'RPM', 'RPM'),
    ('duty', 'percent', 'Fan power', 'Percent', '%%'),
]


class Plugin(openmediavault.mkrrdgraph.IPlugin):
    def create_graph(self, config):
        for graph, kind, title, vlabel, unit in GRAPHS:
            config['instance'] = 'exec-qnapx39-{}'.format(graph)
            image_filename = '{image_dir}/{instance}-{period}.png'.format(
                **config)
            rrd_files = sorted(glob.glob('{}/exec-qnapx39/{}-*.rrd'.format(
                config['data_dir'], kind)))
            if not rrd_files:
                openmediavault.mkrrdgraph.copy_placeholder_image(
                    image_filename)
                continue
            args = [image_filename]
            args.extend(config['defaults'])
            args.extend(['--start', config['start']])
            args.extend(['--title', '"QNAP {}{}"'.format(
                title, config['title_by_period'])])
            args.append('--slope-mode')
            args.extend(['--lower-limit', '0'])
            args.extend(['--vertical-label', vlabel])
            for index, rrd_file in enumerate(rrd_files):
                name = os.path.basename(rrd_file)[len(kind) + 1:-len('.rrd')]
                color = COLORS[index % len(COLORS)]
                args.append('DEF:v{}={}:value:AVERAGE'.format(index, rrd_file))
                args.append('DEF:x{}={}:value:MAX'.format(index, rrd_file))
                args.append('LINE1:v{}{}:"{:<12}"'.format(
                    index, color, LABELS.get(name, name)))
                args.append('GPRINT:x{}:MAX:"%5.0lf {} Max"'.format(
                    index, unit))
                args.append('GPRINT:v{}:LAST:"%5.0lf {} Last\\l"'.format(
                    index, unit))
            args.append('COMMENT:"{last_update}"'.format(**config))
            openmediavault.mkrrdgraph.call_rrdtool_graph(args)
        return 0
