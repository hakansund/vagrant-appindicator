#!/usr/bin/python3

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

import signal

from gi.repository import Gtk as gtk
from gi.repository import AppIndicator3 as appindicator
from gi.repository import Notify as notify

import util
import machineindex
import vagrantcontrol


APPINDICATOR_ID = 'vagrant_appindicator'


class VagrantAppIndicator(object):
    def __init__(self):
        self.indicator = appindicator.Indicator.new(
            APPINDICATOR_ID, util.image_path("icon"), appindicator.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.last_known_machines = None
        # trigger first update manually, and then subscribe to real updates
        self.update(machineindex.get_machineindex())
        machineindex.subscribe(self.update)


    def update(self, machines):
        """Entry point for appindicator update.
        Triggers all UI modifications necessary on updates of machines states
        Subscribed as a listener to updates of machineindex"""
        self.__notify_about_changes(machines)
        self.__update_menu(machines)
        self.last_known_machines = machines


    def _shutdown(self):
        machineindex.unsubscribe_all()


    def quit(self):
        self._shutdown()
        gtk.main_quit()


    def _show_notification(self, title, message):
        """Shows balloon notification with given title and message"""
        notify.Notification("<b>Vagrant - %s</b>" % title, message).show()


    def __notify_machine_state_change(self, title, machine):
        self._show_notification(title, "%s (%s)" % (machine.directory, machine.name))


    def __notify_about_changes(self, new_machines):
        """Shows balloon notifications for every change in machines states"""
        if not self.last_known_machines: return # only possible on first update

        diff = machineindex.diff_machineindexes(new_machines, self.last_known_machines)
        for new_machine in diff[0]:
            self.__notify_machine_state_change("New machine went %s" % new_machine.state, new_machine)
        for removed_machine in diff[1]:
            self.__notify_machine_state_change("Machine destroyed", removed_machine)
        for changed_machine in diff[2]:
            self.__notify_machine_state_change("Machine went %s" % changed_machine.state, changed_machine)


    def __update_menu(self, machines):
        """Updates appindicator menu with current machines state"""
        menu = gtk.Menu()

        for machine in machines:
            item = self.__create_machine_submenu(machine)
            menu.append(item)

        item_quit = gtk.MenuItem('Quit')
        item_quit.connect('activate', self.quit)
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)


    def __create_machine_submenu(self, machine):
        """Creates menu item for a given VM, with its submenu and relvant actions in it"""
        menu_item = gtk.ImageMenuItem("%s (%s) - %s" % (machine.directory, machine.name, machine.state))
        menu_item_image = gtk.Image()
        menu_item_image.set_from_file(util.image_path(machine.state)) # TODO: handle all states
        menu_item.set_image(menu_item_image)
        menu_item.set_always_show_image(True)
        
        submenu = gtk.Menu()
        menu_item.set_submenu(submenu)

        submenu_item_terminal = gtk.MenuItem('Open terminal...')
        submenu_item_terminal.connect('activate', self.on_open_terminal, machine)
        submenu.append(submenu_item_terminal)

        if machine.isPoweroff():
            submenu_item_up = gtk.MenuItem('Up')
            submenu_item_up.connect('activate', self.on_start_vm, machine)
            submenu.append(submenu_item_up)
        
        if machine.isRunning():
            submenu_item_halt = gtk.MenuItem('Halt')
            submenu_item_halt.connect('activate', self.on_halt_vm, machine)
            submenu.append(submenu_item_halt)

        submenu_item_destroy = gtk.MenuItem('Destroy')
        submenu_item_destroy.connect('activate', self.on_destroy_vm, machine)
        submenu.append(submenu_item_destroy)

        return menu_item

    # UI listeners
    def on_open_terminal(self, _, machine): vagrantcontrol.open_terminal(machine)
    def on_start_vm(self, _, machine): vagrantcontrol.start(machine)
    def on_halt_vm(self, _, machine): vagrantcontrol.halt(machine)
    def on_destroy_vm(self, _, machine): vagrantcontrol.destroy(machine)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    notify.init(APPINDICATOR_ID)
    VagrantAppIndicator()
    gtk.main()


if __name__ == "__main__":
    main()
