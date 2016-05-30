# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 13:28:58 2016

@author: jenglish
"""
import re
import argparse
 
import basetaskerplugin

from lib import Task

re_pend = re.compile(r'\s{pend:([^}]*)}')


# noinspection PyIncorrectDocstring,PyIncorrectDocstring
class PendingPlugin(basetaskerplugin.NewCommandPlugin):
    def __init__(self):
        self.after_parser = after = argparse.ArgumentParser('after',
            description="""Create a new task to be done after a
            current task is completed""")
        after.add_argument('tasknum', type=int,
                           help="Task to create the follow-up task from")

        after.add_argument('text', nargs=argparse.REMAINDER)

        self.parsers = {
            after: "Add a follow-up task to a current task",
        }
        super().__init__()

    def activate(self):
        self._log.debug('Activating Pending')
        self.setConfigOption('public_methods', 'do_after')

        super().activate()
    
    def help_after(self):
        self.after_parser.print_help()
        
    # noinspection PyIncorrectDocstring,PyIncorrectDocstring
    def do_after(self, line):
        """Create a new task to be done after a current task is completed"""
        args = self.after_parser.parse_args(line.split())
        
        tasks = self.lib.get_tasks(self.lib.config['Files']['task-path'])
        source = tasks[args.tasknum]
        new_task = Task.from_text(' '.join(args.text))

        
        for context in source.contexts:
            if context not in new_task:
                new_task.text += " {}".format(context)
        for project in source.projects:
            if project not in new_task:
                new_task.text += " {}".format(project)
                
        for ext, val in list(source.extensions.items()):
            if ext in ['pend', 'uid']:
                continue
            if "{%s:" % ext not in new_task:
                new_task.text += " {%s:%s}" % (ext, val)
            else:
                new_task.text = re.sub(r"{%s:([^}]*)}" % ext,
                                  r"{%s:%s}" % (ext, val),
                                  new_task)
        new_task.text += " {pend:%s}" % source.extensions['uid']
        
        new_task.priority = 'Z'
        
        return self.lib.add_task(str(new_task))
        
    def complete_task(self, this):
        for idx, task in self.lib.tasks.items():
            match = re_pend.search(task.text)
            if match:
                if match.group(1) == this.extensions['uid']:
                    self.lib.tasks[idx] = self.lib.reprioritize_task(task, 'A')
                    self._log.debug("Repriotized pended task: %s".format(task))
        return (0, "", this)
