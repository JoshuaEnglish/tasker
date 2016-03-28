# -*- coding: utf-8 -*-
"""
Created on Mon Feb 29 11:51:14 2016

@author: jenglish
"""
import glob
import os
import argparse
import re

from configparser import ConfigParser
from string import Template

workflow_dir = os.path.join(os.path.dirname(__file__), 'workflows')

import basetaskerplugin
import minioncmd

clean_vocab = re.compile(r"^[@+]")


class WorkflowCLI(minioncmd.MinionCmd):
    prompt = "workflow> "

    def __init__(self, completekey='tab', stdin=None, stdout=None, 
                 workflow_dir=None):
        super().__init__('workflow', 
                         completekey=completekey, 
                         stdin=stdin, 
                         stdout=stdout)
        self.workflows = {}
        self._log.debug("Workflows type: %s", type(self.workflows))
        local_dir = workflow_dir or os.path.join(os.path.dirname(__file__), 'workflows')
        for fname in glob.glob(os.path.join(local_dir, "*.workflow")):
            cp = ConfigParser()
            cp.read(fname)
            name = os.path.splitext(os.path.split(fname)[1])[0]
            self.workflows[name] = cp
            
        self._workflow_dir = local_dir
        

    def add_workflow_task(self, flow, stepnum, flow_id):
        """add_workflow_task(flow, stepnum, flow_id)
        
        Adds a new task to the task manager based on the workflow.

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
                
        d = dict(zip(keys, words))
        
        steps = self.workflows[flow]['Steps']
        if str(stepnum) not in steps:
            return None
            
        step = self.workflows[flow]['Steps'][str(stepnum)]
        step += " {wn:$flow} {ws:$step} {wid:$wid}"
        d['flow'] = flow
        d['step'] = stepnum
        d['wid'] = flow_id
        
        new_task = Template(step).safe_substitute(d)
        
        if hasattr(self, 'master'):
            self.master.cmdqueue.append('add {}'.format(new_task))
            self._log.info("Adding task: %s", new_task)
        
    def do_start(self, text):
        """Adds the first step of a workflow to the task list.
        The first word in text should be the name of the workflow.
        Subsequent words are paired with the workflow's vocabulary to 
        fill out the step template.
        """

        text = text.strip()
        words = text.split()
        flow = words.pop(0)
        if flow not in self.workflows:
            self._log.error("Missing workflow: %s", flow)
            print("Missing workflow: {}".format(flow))
            return None

        # remove any '+' or '@' characters entered
        words = [clean_vocab.sub('', w) for w in words]

        instances = self.workflows[flow]['Instances']
        self._log.debug("Instance IDs: %s", ','.join(instances.keys()))
        next_id = max([int(i) for i in instances.keys()], default=0) + 1

        instances[str(next_id)] = ','.join(words)
        self.add_workflow_task(flow, 1, next_id)
        with open(os.path.join(self._workflow_dir, "%s.workflow" % flow),'w') as fp:
            self.workflows[flow].write(fp)
        return None
           
    def do_list(self, text):
        """list current workflows"""
        print("Workflow list:", file=self.stdout)
        for idx, flow in enumerate(self.workflows, start=1):
            print(idx, flow, file=self.stdout)
        print()
            
    def do_info(self, text):
        """Print the details of a given workflow"""
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Workflow'].items():
            print(key, val, sep=": ")
        print()
            
    def do_steps(self, text):
        """Print the step templates of a given workflow"""
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Steps'].items():
            print(key, val, sep=": ")
        print()
        
    def do_instances(self, text):
        """Prints a list of known instances"""
        text = text.strip()
        if text not in self.workflows:
            print('No workflow "{}" found'.format(text))
            return
        for key, val in self.workflows[text]['Instances'].items():
            print(key, val, sep=": ")
        print()
        
    def do_create(self, text):
        """Create a new workflow: create NAME"""
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
        print("When entering steps, use $<word> to define the vocabulary for this workflow.")
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
        

class Workflow(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug("Activating Workflows")
        if not self.hasConfigOption('directory'):
            self._log.debug("Setting Directory to default")
            self.setConfigOption('directory', workflow_dir)

        if not self.hasConfigOption('hidden-extensions'):
            self.setConfigOption('hidden-extensions', 'wid,ws,wn')
        
        
        local_dir = self.getConfigOption('directory')
        
        self.cli_name = 'workflow'
        self.cli = WorkflowCLI() # needs to be an instance
        
#        self._log.debug("Adding workflow commands")
       
        parser = self.parser = argparse.ArgumentParser('workflow')
        self.helpstr = 'Workflows commands (see `help workflow`)'
        workflow_commands = parser.add_subparsers(title='workflow commands', 
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
                

    def complete_task(self, c, p, s, e, t, o, j, x):
        self._log.debug('Workflow checking completed task %s', 
                        x.get('uid', 'NO ID'))
        if 'wn' in x:
            flow = self.cli.workflows[x['wn']]
            steps = flow['Steps']
            if x['ws'] not in steps:
                msg = "Workflow {} does not have step {}".format(flow, x['ws'])
                self._log.error(msg)
                print(msg) # this will cause problems down the road
                return (0, None, c, p, s, e, t)
            next_step = str(int(x['ws'])+1)
            if next_step in steps:
                try:
                    self.cli.add_workflow_task(x['wn'], next_step, x['wid'])
                except KeyError as E:
                    return(2,E, c, p, s, e, t)
        return(0, None, c, p, s, e, t)
    


if __name__=='__main__':
    w =WorkflowCLI()
    w.cmdloop()