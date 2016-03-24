# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 13:28:58 2016

@author: jenglish
"""
import re
import argparse
 
import basetaskerplugin

re_pend = re.compile(r"\s{pend:([^}]*)}")


# noinspection PyIncorrectDocstring,PyIncorrectDocstring
class PendingPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Pending')
        self.setConfigOption('public_methods', 'do_after')
        if not self.hasConfigOption('hide_pend_ext'):
            self.setConfigOption('hide_pend_ext', 'true')
        
       
        self.after_parser = after = argparse.ArgumentParser('after')
        after.add_argument('tasknum', type=int,
                             help="Task to create the follow-up task from")
        after.add_argument('text', nargs=argparse.REMAINDER)

        self.parsers = {
            after: "Add a follow-up task to a current task",
        }

        super().activate()
    
    def hide_pend_extension(self):
        self.lib.config.set(self.CONFIG_SECTION_NAME, 'hide_pend_ext', 'true')
        self.lib.hide_extension('pend')
        
    def show_pend_extension(self):
        self.setConfigOption('hide_pend_ext', 'false')
        self.lib.show_extension('show')

    # noinspection PyIncorrectDocstring,PyIncorrectDocstring
    def do_after(self, line):
        """Create a new task to be done after a current task is completed"""
        args = self.after_parser.parse_args(line.split())
        
        tasks = self.lib.get_tasks(self.lib.config['Files']['task-path'])
        source_stuff = self.lib.parse_task(tasks[args.tasknum])
        new_task = ' '.join(args.text)
        
        for context in source_stuff[5]:
            if context not in new_task:
                new_task += " {}".format(context)
        for project in source_stuff[6]:
            if project not in new_task:
                new_task += " {}".format(project)
                
        for ext, val in list(source_stuff[7].items()):
            if ext in ['pend', 'uid']:
                continue
            if "{%s:" % ext not in new_task:
                new_task += " {%s:%s}" % (ext, val)
            else:
                new_task = re.sub(r"{%s:([^}]*)}" % ext,
                                  r"{%s:%s}" % (ext, val),
                                  new_task)
        new_task += " {pend:%s}" % source_stuff[7]['uid']
        
        new_stuff = self.lib.parse_task(new_task)
        new_pri = new_stuff[1] if source_stuff[0] else 'Z'
        
        return self.lib.add_task(self.lib.graft(False, new_pri, *new_stuff[2:5]))
        
    def complete_task(self, c, p, s, e, t, o, j, x):
        for idx, text in self.lib.tasks.items():
            match = re_pend.search(text)
            if match:
                if match.group(1) == x['uid']:
                    self.lib.tasks[idx] = self.lib.reprioritize_text(text, 'A')
                    self._log.debug("Repriotized pended task: %s".format(t))
        return (0, "", c, p, s, e, t)
        
        
        