# Copyright 2014, candidtim (https://github.com/candidtim)
#
# This file is part of Vagrant AppIndicator for Ubuntu.
#
# Vagrant AppIndicator for Ubuntu is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# Foobar is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with Foobar.
# If not, see <http://www.gnu.org/licenses/>.

'''
Parsers for Vagrant machine-index file
'''

import os
import json

from gi.repository import Gio as gio


__VAGRNAT_HOME_VAR = "VAGRANT_HOME"
__MACHINE_INDEX_PATH = "data/machine-index/index"


# module's public interface

class Machine(object):
    def __init__(self, id, state, directory, name):
        self.id = id
        self.state = state
        self.directory = directory
        self.name = name
    
    def isPoweroff(self):
        return self.state == "poweroff"

    def isRunning(self):
        return self.state == "running"

    def __str__(self):
        return "id=%s state=%s directory=%s name=%s" % \
            (self.id, self.state, self.directory, self.name)

    def __eq__(self, other):
        return self.id == other.id

    def _changed_state_since(self, other):
        assert self == other
        return self.state != other.state


class MachineIndexNotFoundError(Exception):
    pass


def get_machineindex():
    machineindex_path = _resolve_machineindex_path()
    with open(machineindex_path, 'r') as machineindex_file:
        return _parse_machineindex(machineindex_file)


def diff_machineindexes(new_index, old_index):
        '''Returns tuple of 3 items: 
        (list of new machines, list of removed machines, list of machines that changed state)
        '''
        new_machines = [machine for machine in new_index if machine not in old_index]
        removed_machines = [machine for machine in old_index if machine not in new_index]
        changed_machines = [machine for machine in new_index 
            if machine in old_index and machine._changed_state_since(old_index[old_index.index(machine)])]
        went_running = [machine for machine in changed_machines if machine.isRunning()]
        return (new_machines, removed_machines, changed_machines)


active_monitors = {}

def subscribe(listener):
    def on_machineindex_change(mon, f, o, event):
        if event == gio.FileMonitorEvent.CHANGES_DONE_HINT:
            listener(get_machineindex())

    machineindex_path = _resolve_machineindex_path()
    file_to_monitor = gio.File.new_for_path(machineindex_path)
    monitor = file_to_monitor.monitor_file(gio.FileMonitorFlags.NONE, None)
    handler_id = monitor.connect("changed", on_machineindex_change)
    active_monitors[handler_id] = monitor

def unsubscribe_all():
    global active_monitors
    for handler_id in active_monitors:
        monitor = active_monitors[handler_id]
        monitor.disconnect(handler_id)
    active_monitors = {}


# private implementation

def _resolve_machineindex_path():
    vagrant_home = os.getenv(__VAGRNAT_HOME_VAR, "~/.vagrant.d")
    machineindex_path = os.path.expanduser(os.path.join(vagrant_home, __MACHINE_INDEX_PATH))
    if not os.path.isfile(machineindex_path):
        raise MachineIndexNotFoundError(
            "Vagrant machine index not found. Is Vagrant installed and at least one VM created?")
    return machineindex_path


def _parse_machineindex(machineindex_file):
    machineindex_json = json.load(machineindex_file)
    version = machineindex_json["version"]
    # currently, only one parser version is available:
    parser = __MachineIndexParserV1() 
    return parser.parse(machineindex_json)


class __MachineIndexParser(object):
    def parse(self, machineindex_json):
        raise NotImplementedError()


class __MachineIndexParserV1(__MachineIndexParser):
    def parse(self, machineindex_json):
        machineindex = []
        machines_json = machineindex_json["machines"]
        for machine_id in machines_json:
            machine_json = machines_json[machine_id]
            machine = Machine(machine_id, machine_json["state"], 
                machine_json["vagrantfile_path"], machine_json["name"])
            machineindex.append(machine)
        return tuple(machineindex)
