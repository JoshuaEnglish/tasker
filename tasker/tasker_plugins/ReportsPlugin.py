# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 15:12:07 2016

@author: jenglish
"""

import basetaskerplugin

class ReportsPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Reports')
        self.setConfigOption('public_methods', 'do_projects,do_contexts')
        super().activate()
        
    def do_projects(self, text):
        """Print a list of current projects with the number of open and closed tasks"""
        project_report()
        
    def do_contexts(self, text):
        context_report()
        
