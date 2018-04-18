# -*- coding: utf-8 -*-
"""
About Workflow
==============

These commands allow you to create sequential tasks for projects that
are the same process but for different contexts: processing orders for
different customers or verifying lists of data that are the same form.

Using Workflows
---------------

The inspiration for this was a quoting processing for sales support:

    1. Sales rep requests a pricing quote
    2. Support rep verifies all information
    3. Support rep creates the quote
    4. Support rep submit quote for pricing
    5. Pricing returns quote to support rep
    6. Support rep returns pricing to sales rep

The support rep also had to log each of these steps in a separate job tracker.

Using the quote as a project name and giving all of these steps a @pricing
context, the following workflow was created:

    1. (A) Log @pricing request for +$project
    2. (B) Confirm +$project information with $salesrep @pricing
    3. (A) Submit +$project to @pricing team
    4. (A) Check for +$project @pricing approval
    5. (A) Send +$project @pricing to $salesrep

(The support rep was comfortable using the @pricing context in the middle
of a sentence. It's a style choice.)

In practice, as sales rep Jane Schmo contacts the support rep for a pricing
quote on the Giganta Corp Land Grab, the rep starts things in tasker with::

    tasker> workflow start GigantaLandGrab JSchmo
    (A) Log @pricing request for +GigantaLandGrab

    tasker> list
    1 (A) Log @pricing request for +GigantaLandGrab

(There are extensions being written to the file. They are hidden by default.)

From there, as each step is completed, the sales rep doesn't need to return
to the workflow command, but treat these as normal tasks::

    tasker> do 1
    x Log @pricing request for +GigantaLandGrab
    (B) Confirm +GigantaLandGrab information with JSchmo @pricing

    tasker> list
    2 (B) Confirm +GigantaLandGrab information with JSchmo @pricing

When the last task in the workflow is marked as complete, no new tasks are
added at runtime.

Creating Workflows
------------------
"""

import glob
import os
import argparse
import re

from configparser import ConfigParser
from string import Template

import basetaskerplugin
import minioncmd

WORKFLOWS = os.path.join(os.path.dirname(__file__), 'workflows')

CLEAN_VOCABULARY = re.compile(r"^[@+]")

__todo__ = """
2017-04-14: Local branches.
add a wx key that would read the next step, otherwise
grab the next task number. wx:0 could end a branch.

If a workflow requires interacting with separate systems, they can
be joined in one workflow. wx should allow for comma-dileneated numbers

2017-09-18: Move library logic to an actual library
There is logic in the CLI that should be handled by a library or the plugin
object itself. The CLI object does not know about the Plugin, but the Plugin
knows about the CLI.
"""


class WorkflowLib(object):
    pass


class WorkflowCLI(minioncmd.MinionCmd):
    prompt = "workflow>"
    minion_header = "Other subcommands (type <topic> help)"
    doc_leader = """Workflow Help

    Create and use pre-programmed tasks to generate sequentially without
    clogging up the Z-priority list
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 workflow_dir=None):
        super().__init__('workflow',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.workflows = {}
        self._log.debug("Workflows type: %s", type(self.workflows))
        local_dir = workflow_dir or WORKFLOWS
        for fname in glob.glob(os.path.join(local_dir, "*.workflow")):
            flow_prefs = ConfigParser()
            flow_prefs.read(fname)
            name = os.path.splitext(os.path.split(fname)[1])[0]
            self.workflows[name] = flow_prefs

        self._workflow_dir = local_dir

    def add_workflow_task(self, flow, stepnum, flow_id):
        """add_workflow_task(flow, stepnum, flow_id)

        Adds a new task to the task manager based on the workflow.
        This method is called during the `do_complete` hook.

        :param str flow: name of the workflow to follow
        :param int/str stepnum: number of the step
        :param int flow_id: the instance Id for the workflow
        """
        if flow not in self.workflows.keys():
            self._log.error("Missing workflow: %s", flow)
            return None
        flow_id = str(flow_id)
        if flow_id not in self.workflows[flow]['Instances']:
            self._log.error("Missing %s workflow instance %s", flow, flow_id)
            print("Missing %s workflow instance %s" % (flow, flow_id))
            raise KeyError("Missing %s workflow instance %s" % (flow, flow_id))

        words = [word.strip() for word in
                 self.workflows[flow]['Instances'][flow_id].split(',')]

        keys = [key.strip() for key in
                self.workflows[flow]['Workflow']['vocabulary'].split(',')]

        subs = dict(zip(keys, words))

        steps = self.workflows[flow]['Steps']
        if str(stepnum) not in steps:
            return None

        step = self.workflows[flow]['Steps'][str(stepnum)]
        step += " {wn:$flow} {ws:$step} {wid:$wid}"
        subs['flow'] = flow
        subs['step'] = stepnum
        subs['wid'] = flow_id

        new_task = Template(step).safe_substitute(subs)

        if hasattr(self, 'master'):
            self.master.cmdqueue.append('add {}'.format(new_task))
            self._log.info("Adding task: %s", new_task)
        else:
            self._log.error("No BossCmd instance to add task with")

    def do_start(self, text):
        """Usage: start NAME VOCABULARY+

        Add the first step of a workflow to the task list.
        The first word in text should be the name of the workflow.
        Subsequent words are paired with the workflow's vocabulary to
        fill out the step template.

        Call info NAME to get relevant vocabulary.
        """

        text = text.strip()
        words = text.split()
        flow = words.pop(0)
        # At this point, everything should be done by a library
        if flow not in self.workflows:
            self._log.error("Missing workflow: %s", flow)
            print("Missing workflow: {}".format(flow))
            return None

        # remove any '+' or '@' characters entered
        words = [CLEAN_VOCABULARY.sub('', w) for w in words]

        instances = self.workflows[flow]['Instances']
        self._log.debug("Instance IDs: %s", ','.join(instances.keys()))
        next_id = max([int(i) for i in instances.keys()], default=0) + 1

        instances[str(next_id)] = ','.join(words)
        self.add_workflow_task(flow, 1, next_id)
        path = os.path.join(self._workflow_dir, "%s.workflow" % flow)
        with open(path, 'w') as fp:
            self.workflows[flow].write(fp)
        return None

    def do_list(self, text):
        """Usage: list

        List current workflows
        """
        print("Workflow list:", file=self.stdout)
        for idx, flow in enumerate(self.workflows, start=1):
            print(idx, flow, file=self.stdout)
        print()

    def do_info(self, text):
        """Usage: info NAME

        Print the details of a given workflow.
        """
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Workflow'].items():
            print(key, val, sep=": ")
        print()

    def do_steps(self, text):
        """Usage: steps NAME

        Print the step templates of a given workflow.
        """
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Steps'].items():
            print(key, val, sep=": ")
        print()

    def do_instances(self, text):
        """Usage: instances NAME

        Prints a list of known instances.
        """
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Instances'].items():
            print(key, val, sep=": ")
        print()

    def do_create(self, text):
        """Usage: create NAME

        Create a new workflow. A wizard collects the necessary information.
        """
        newname = text.strip().split()

        if len(newname) == 0:
            self._log.error("No name specified")
            print("Please provide a single-word-name for the new workflow")
            return None

        if len(newname) > 1:
            self._log.error("Too many names given for workflow")
            print("Please provide a single-word name for the workflow")
            return None

        newname = newname[0]
        if newname in self.workflows:
            self._log.error('Workflow %s already exists', newname)
            print("Workflow %s already existis" % newname)
            return None

        keep_going = True
        desc = input("Please enter a description for this workflow: ")
        steps = []
        vocabulary = []
        print("When entering steps, use $<word> to define the vocabulary "
              "for this workflow.")
        print("Enter a blank line to complete this process.")
        while keep_going:
            step = input("Describe step number %d: " % (len(steps)+1))

            if step:
                steps.append(step)
                words = step.split()
                for word in words:
                    if word.startswith('$'):
                        candidate = word[1:]
                        if candidate not in vocabulary:
                            vocabulary.append(candidate)
            else:
                keep_going = False
        #  At this point, everything should be passed to a library
        print("Vocabulary: %s" % ', '.join(vocabulary))

        cp = ConfigParser()
        cp.add_section('Workflow')
        cp.set('Workflow', 'name', newname.title())
        cp.set('Workflow', 'description', desc)
        cp.set('Workflow', 'vocabulary', ','.join(vocabulary))

        cp.add_section('Steps')
        for idx, step in enumerate(steps, 1):
            cp.set('Steps', str(idx), step)

        cp.add_section('Instances')

        fname = "%s.workflow" % newname.lower()
        fpath = os.path.join(self._workflow_dir, fname)
        with open(fpath, 'w') as fp:
            cp.write(fp)

        cp.write(self.stdout)
        self.workflows[newname] = cp
        print()
        print("Created new workflow in", fpath)

    def do_abandon(self, text):
        """Usage: abandon TASKNUM REASON+

        Abandons an established workflow.
        """
        # if ask for workflow name and ID, need to identify the tasknum
        # should expect the tasknum
        # get the worflow name and id
        # determine the last step of the workflow
        # set the task ws extension to the last step
        # add a note to the item stating it is abandoned.
        # use self.master.cmdqueue
        if not hasattr(self, 'master'):
            self._log.error("No BossCmd Instance to handle request")
            return True
        tasknum, reason = re.match(r"(\d+)\s+(.*)", text).groups()
        tasknum = int(tasknum)

        tasks = self.master.lib.build_task_dict()

        selected_victim = tasks[tasknum]
        if tasknum not in tasks.keys():
            self._log.error("Task does not exist")
            print("Task does not exist")
            return True

        flow_name = selected_victim.extensions['wn']

        steps = self.workflows[flow_name]['Steps']
        last_step = max(steps)

        new_version = re.sub(r"{ws:\d+}", "{ws:%s}" % last_step,
                             selected_victim.text)
        Task = tasks[tasknum].__class__
        tasks[tasknum] = Task.from_text(new_version)
        self.master.lib.tasks = tasks
        self.master.cmdqueue.append(
            "do {} Abandoned: {}".format(tasknum, reason))
        return True

    def do_edit(self, text):
        """Opens the workflow file in the default editor"""
        workflow_path = os.path.join(self._workflow_dir, "%s.workflow" % text)
        if not os.path.exists(workflow_path):
            msg = "Workflow file %s does not exist" % text
            self._log.error(msg)
            self.print(msg)
            return None
        editor_path = self.master.config.get('Tasker', 'editor')
        if os.path.exists(editor_path):
            import subprocess
            subprocess.Popen("%s %s" % (editor_path, workflow_path))
        else:
            os.startfile(workflow_path)

    def do_skip(self, text):
        "skip num - adds the next task in the workflow; leaves the task open"
        tasknum, reason = re.match(r"(\d+)\s+(.*)", text).groups()
        tasknum = int(tasknum)

        tasks = self.master.lib.build_task_dict()

        if tasknum not in tasks.keys():
            self._log.error("Task does not exist")
            print("Task does not exist")
            return True
        victim = tasks[tasknum]

        if 'wn' not in victim.extensions:
            self._log.error("Task not part of a workflow")
            print("Task not part of a workflow")
            return True

        if 'ws' not in victim.extensions:
            self._log.error("Task does not have step. Major failue")
            print("Task has workflow name but no workflow step. Major issue")
            return True

        this_step = int(victim.extensions['ws'])
        # complete_task hook only checks for the workflow name.
        # keeping the rest of the extensions allows to search by step as well
        # as by project
        new_text = re.sub(r"\s*{wn:%s}" % victim.extensions['wn'],
                          "", str(victim))
        print(new_text)
        tasks[tasknum] = victim.from_text(new_text)
        self.master.lib.tasks = tasks
        self.master.lib.write_current_tasks()
        self.add_workflow_task(victim.extensions['wn'],
                               str(this_step + 1),
                               victim.extensions['wid'])

    def help_about(self):
        """About this plugin"""
        print("""These commands allow you to create sequential tasks for projects that
are the same process but for different contexts: processing orders for
different customers or verifying lists of data that are the same form.""")


class Workflow(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug("Activating Workflows")
        if not self.hasConfigOption('directory'):
            self._log.debug("Setting Directory to default")
            self.setConfigOption('directory', WORKFLOWS)

        if not self.hasConfigOption('hidden-extensions'):
            self.setConfigOption('hidden-extensions', 'wid,ws,wn')

        self.cli_name = 'workflow'
        self.cli = WorkflowCLI()  # needs to be an instance

        parser = self.parser = argparse.ArgumentParser('workflow')
        self.helpstr = 'Workflows commands (see `help workflow`)'
        workflow_commands = parser.add_subparsers(title='workflow commands',
                                                  dest='subcommand',
                                                  metavar='')
        start_workflow = workflow_commands.add_parser(
            'start', help='start a workflow')
        start_workflow.add_argument(
            'name', help="The name of the workflow to start")
        start_workflow.add_argument(
            'vocabulary', nargs=argparse.REMAINDER,
            help="The vocabulary for the workflow instance")

        workflow_commands.add_parser('list', help='lists known workflows')

        steps = workflow_commands.add_parser(
            'steps',
            help='displays templated steps for a given workflow')
        steps.add_argument('text', nargs=argparse.REMAINDER)

        instance = workflow_commands.add_parser(
            'instances',
            help='displays known instances of a workflow')
        instance.add_argument('workflow')

        info = workflow_commands.add_parser(
            'info',
            help="displays information about a workflow")
        info.add_argument('workflow')

        create = workflow_commands.add_parser(
            'create',
            help="creates a new workflow file")
        create.add_argument('name', help="the name of the workflow to create")
        create.add_argument('--edit', help="launch the editor automatically")

        skip = workflow_commands.add_parser(
            'skip',
            help='Triggers next task in workflow leaving current task open')
        skip.add_argument('tasknum', type=int,
                          help='Task number')
        skip.add_argument('reason', nargs=argparse.REMAINDER)

        super().activate()

    def complete_task(self, this):
        self._log.debug('Workflow checking completed task %s',
                        this.extensions.get('uid', 'NO ID'))
        if 'wn' in this.extensions:
            flow = self.cli.workflows[this.extensions['wn']]
            steps = flow['Steps']
            if this.extensions['ws'] not in steps:
                msg = "Workflow {} does not have step {}".format(
                    flow,
                    this.extensions['ws'])
                self._log.error(msg)
                print(msg)  # this will cause problems down the road
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
