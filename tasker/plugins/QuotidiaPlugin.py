# -*- coding: utf-8 -*-
"""
About Quotidia
==============

Quotidia allows you to schedule tasks to appear in your task list 
under certain time-given constraints. For example, a reminder to
pay rent on the first of each month, or to run a report every Monday.

Each quotidium needs the following attributes:
QID: System generated quote ID
Text to add: including the Priority, if any
Day Filter: SMTWRFY - any letter matching the days it should run
Time Filter: first time the task should be listed (hold off on this idea)
Last Addition: datetime stamp of the last time this item was added.

Basic idea: On load, this should scan the quotidia and see if today matches
a day the quotidium should be run. Then compare the last addition time to the
current time. If it has appeared in the last 24 hours ... hold on. That won't work
if I don't launch the program until the afternoon on Monday, then everything will
be delayed until the next afternoon. I just need to check if the thing was run 
on the same day as today. This can be a day check.
"""

import glob
import os
import argparse
import re

from configparser import ConfigParser
from string import Template

import basetaskerplugin
import minioncmd

QUOTIDIA = os.path.join(os.path.dirname(__file__), 'quotidia')


CLEAN_VOCABULARY = re.compile(r"^[@+]")

CLI_ABOUT = """Quotidia allows you to define tasks on a recurring basis."""


class QuotidiaCLI(minioncmd.MinionCmd):
    prompt = "quotidia> "
    minion_header = "Other subcommands (type <topic> help)"
    doc_leader = """Quotidia Help

    Create and use pre-programmed tasks to generate sequentially without
    clogging up the Z-priority list
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 quotidia_dir=None):
        super().__init__('quotidia',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.quotidia = {}
        self._log.debug("Quotidias type: %s", type(self.Quotidias))
        local_dir = quotidia_dir or QUOTIDIA
        for fname in glob.glob(os.path.join(local_dir, "*.quotidia")):
            flow_prefs = ConfigParser()
            flow_prefs.read(fname)
            name = os.path.splitext(os.path.split(fname)[1])[0]
            self.quotidias[name] = flow_prefs

        self._quotidia_dir = local_dir


    
    def do_list(self, text):
        """Usage: list

        List current quotidia
        """
        print("Quotidia list:", file=self.stdout)
        for idx, flow in enumerate(self.quotidia, start=1):
            print(idx, flow, file=self.stdout)
        print()

    def do_info(self, text):
        """Usage: info NAME

        Print the details of a given quotidia.
        """
        text = text.strip()
        if text not in self.quotidia:
            print('No quotidia "{}" found'.format(text))
            return
        for key, val in self.quotidia[text]['Quotidia'].items():
            print(key, val, sep=": ")
        print()


    def do_create(self, text):
        """Usage: create NAME

        Create a new quotidia. A wizard collects the necessary information.
        """
        newname = text.strip().split()

        if len(newname) == 0:
            self._log.error("No name specified")
            print("Please provide a single-word name for the new workflow")
            return None

        if len(newname) > 1:
            self._log.error("Too many names given for workflow")
            print("Please provide a single-word name for the workflow")
            return None

        newname = newname[0]
        if newname in self.quotidia:
            self._log.error('Quotidia %s already exists', newname)
            print("Quotidia %s already existis" % newname)
            return None

        keep_going = True
        """QID: System generated quote ID
Text to add: including the Priority, if any
Day Filter: SMTWRFY - any letter matching the days it should run
Time Filter: first time the task should be listed (hold off on this idea)
Last Addition: datetime stamp of the last time this item was added."""
        text = input("Please enter the text for this quotidia: ")
        
        day_ok = False
        while not day_ok:
            days = input("Please enter the days to run")
        

        cp = ConfigParser()
        cp.add_section('Quotidia')
        cp.set('Quotidia', 'name', newname.title())
        cp.set('Quotidia', 'task', text)

 
        fname = "%s.quotidia" % newname.lower()
        fpath = os.path.join(self._workflow_dir, fname)
        with open(fpath, 'w') as fp:
            cp.write(fp)

        cp.write(self.stdout)
        self.workflows[newname] = cp
        print()
        print("Created new quotidia in", fpath)


    def help_about(self):
        """About this plugin"""
        print(CLI_ABOUT)

class Quotidia(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug("Activating Quotidia")
        if not self.hasConfigOption('directory'):
            self._log.debug("Setting Directory to default")
            self.setConfigOption('directory', QUOTIDIA)

        if not self.hasConfigOption('hidden-extensions'):
            self.setConfigOption('hidden-extensions', 'qid')

        self.cli_name = 'quotidia'
        self.cli = QuotidiaCLI() # needs to be an instance

        parser = self.parser = argparse.ArgumentParser('quotidia')
        self.helpstr = 'Quotidia commands (see `help quotidia`)'
        workflow_commands = parser.add_subparsers(title='quotidia commands',
                                                  dest='subcommand',
                                                  metavar='')
        start_workflow = workflow_commands.add_parser('start', help='start a workflow')
        start_workflow.add_argument('name', help="The name of the workflow to start")
        start_workflow.add_argument('vocabulary', nargs=argparse.REMAINDER,
                                    help="The vocabulary for the workflow instance")
#
        workflow_commands.add_parser('list', help='lists known workflows')

        steps = workflow_commands.add_parser('steps',
                                             help='displays templated steps for a given workflow')
        steps.add_argument('text', nargs=argparse.REMAINDER)

        instance = workflow_commands.add_parser('instances',
                                                help='displays known instances of a workflow')
        instance.add_argument('workflow')

        info = workflow_commands.add_parser('info',
                                            help="displays information about a workflow")
        info.add_argument('workflow')

        create = workflow_commands.add_parser('create',
                                              help="creates a new workflow file")
        create.add_argument('name', help="the name of the workflow to create")
        create.add_argument('--edit', help="launch the editor automatically")

        super().activate()


    def complete_task(self, this):
        self._log.debug('Quotidia checking completed task %s',
                        this.extensions.get('uid', 'NO ID'))
        if 'wn' in this.extensions:
            flow = self.cli.workflows[this.extensions['wn']]
            steps = flow['Steps']
            if this.extensions['ws'] not in steps:
                msg = "Workflow {} does not have step {}".format(flow, this.extensions['ws'])
                self._log.error(msg)
                print(msg) # this will cause problems down the road
                return (0, None, this)
            next_step = str(int(this.extensions['ws'])+1)
            if next_step in steps:
                try:
                    self.cli.add_workflow_task(this.extensions['wn'],
                                               next_step,
                                               this.extensions['wid'])
                except KeyError as E:
                    return(2, E, this)
        return(0, None, this)


