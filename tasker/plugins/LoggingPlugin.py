# -*- coding: utf-8 -*-
"""
About Logging

This is a sample plugin that demonstrates the two ways plugin "hook" methods
are called.

All hook methods must return a tuple of (0, "", task_object) or
(2, "error message", task_object)


"""

import basetaskerplugin


class Logging(basetaskerplugin.TaskerPlugin):
    def activate(self):
        self._log.debug("Activating Workflows")
        super().activate()

    def print_name(self):
        print("This is the logging plugin")

    def add_task(self, this):
        print("Adding task: {:s}".format(this.text))
        return (0, "", this)

    def complete_task(self, this):
        print("Completing task: {:s}".format(this.text))
        return (0, "", this)
