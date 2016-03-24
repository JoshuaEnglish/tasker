# -*- coding: utf-8 -*-
"""
Created on Mon Feb 29 11:51:14 2016

@author: jenglish
"""

import basetaskerplugin

class Logging(basetaskerplugin.TaskerPlugin):
    def activate(self):
        self._log.debug("Activating Workflows")
        super().activate()
        
    def print_name(self):
        print("This is the logging plugin")
        
    def add_task(self, c, p, s, e, t, o, j, x):
        print("Adding task: {}".format(t))
        return (0, "", c, p, s, e, t)
        
    def complete_task(self, c, p, s, e, t, o, j, x):
        print("Completing task: {}".format(t))
        return (0, "", c, p, s, e, t)