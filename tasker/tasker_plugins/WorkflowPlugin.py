# -*- coding: utf-8 -*-
"""
Created on Mon Feb 29 11:51:14 2016

@author: jenglish
"""
import os
import glob

from configparser import ConfigParser

import basetaskerplugin
import minioncmd


workflow_dir = os.path.join(os.path.dirname(__file__), 'workflows')


class WorkflowCmd(minioncmd.MinionCmd):
    prompt = "workflow> "
    plugin_object = None

    def do_list(self, line):
        """Lists known workflows"""
        print("Current Workflows: ", end=None)
        print(self.plugin_object.workflows.keys(), sep=", ")


class Workflow(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        print("Activating Workflows")
        if not self.hasConfigOption('directory'):
            print("Setting default workflow directory...")
            self.setConfigOption('directory', workflow_dir)
        
        if not self.hasConfigOption('public_methods'):
            self.setConfigOption('public_methods', 'start_workflow')
            
        local_dir = self.getConfigOption('directory')
        self.workflows = {}
        for fname in glob.glob(os.path.join(local_dir, "*.workflow")):
            cp = ConfigParser()
            cp.read(fname)
            name = os.path.splitext(os.path.split(fname)[1])[0]
            self.workflows[name] = cp
        super().activate()

    def start_workflow(self, workflow, project):
        """start_workflow(workflow, project)
        Create the first todo in the workflow.
        """
        if workflow not in self.workflows:
            return (2, "Workflow {} not defined".format(workflow), "", "", "", "", "")
