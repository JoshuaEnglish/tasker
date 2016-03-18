# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 14:28:15 2016

@author: jenglish
"""
import os
import re
import datetime
import logging

from operator import itemgetter

TIMEFMT = '%Y-%m-%dT%H:%M:%S'
IDFMT = '%H%M%S%d%m%y'

re_task = re.compile(
    r"(?P<complete>x\s)?"
    r"(?P<priority>[(][A-Z][)]\s)?"
    r"(?P<start>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<end>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<text>.*)"
)

re_context = re.compile("\s([@][-\w]+)")
re_project = re.compile("\s([+][-\w]+)")

re_ext = re.compile(r"\s{\w+:[^}]*}")
re_uid = re.compile(r"\s{uid:[^}]*}")
#re_pend = re.compile(r"\s{pend:([^}]*)}")
re_note = re.compile('\s#\s.*$')

TASK_OK = 0
TASK_ERROR = 1
TASK_EXTENSION_ERROR = 2

first = itemgetter(0)
second = itemgetter(1)
        
class TaskLib(object):
    
    
    def __init__(self, config=None, manager=None): 
        super().__init__()
        
        self.config = config
        self.manager = manager
        
        self.extension_hiders = {}
        
        self.log = logging.getLogger('tasklib')
        
        if not os.path.exists(config['Files']['tasker-dir']):
            os.mkdir(config['Files']['tasker-dir'])
        
        for path in ['task-path', 'done-path']:
            if not os.path.exists(config['Files'][path]):
                fd = open(config['Files'][path], 'w')
                fd.close()

    def parse_task(self, text):
        """Return a tuple of the following fields:
            complete - boolean 
            priority - single letter (blank if complete or unprioritized)
            start - datetime.datetime object
            end - datetime.datetime object or None
            task - remaining text (including any projects or contexts)
            contexts - tuple of contexts (including '@')
            projects - tuple of projects (including '+')
            extensions - dictionary of extension values
            :type text: str
            :param text: text of a task.
        """
        text = text.strip()
        match = re_task.match(text)
        if not any(match.groups()):
            raise ValueError('Task did not parse')
        complete = bool(match.group('complete'))

        priority = match.group('priority')[1] if match.group('priority') else ''

        if match.group('start'):
            start = datetime.datetime.strptime(match.group('start').strip(), TIMEFMT)
        else:
            start = datetime.datetime.now()
    
        if match.group('end'):
            end = datetime.datetime.strptime(match.group('end').strip(), TIMEFMT)
        else:
            end = None
    
        task = match.group('text').strip()
    
        context = [t.strip() for t in re_context.findall(text)]
        projects = [t.strip() for t in re_project.findall(text)]
        extensions = re_ext.findall(text)
        edict = {}
        for ext in extensions:
            key, val = ext.split(':', 1)
            key = key.replace(' {', '')
            val = val.replace('}', '')
            edict[key] = val.strip()
        if 'uid' not in edict:
            edict['uid'] = start.strftime(IDFMT)
            task += " {uid:%s}" % edict['uid']
        return complete, priority, start, end, task, context, projects, edict


    def graft(self, complete, priority, start, end, text):
        """Return a single line of text representing the task.
        Does not append a line return
        :param boolean complete: True if task has been completed
        :param str priority: Single letter A-W for priority, or blank
        :param datetime.datetime start: Time the task was added to the list
        :param datetime.datetime end: Time the task was completed (or None)
        :param str text: remaining text of the task
        :return: string representation of the task
        """
        res = []
        if complete:
            res.append('x')
        if priority and not complete:
            res.append('(%s)' % priority)
        if start:
            res.append(start.strftime(TIMEFMT))
        if end:
            res.append(end.strftime(TIMEFMT))
        res.append(text.strip())
        return " ".join(res)
    
    
    def get_tasks(self, path):
        """Returns a dictionary of (line number (starting at 1), task text) pairs
        :rtype: dict
        :param path: path to the file to read
        :return: dictionary of line number, text pairs
        """
        res = {}
        with open(path, 'r') as fp:
            idx = 1
            for line in fp.readlines():
                if line.strip():
                    res[idx] = line.strip()
                    idx += 1
        return res
    
    
    def write_tasks(self, task_dict, local_path):
        """write_tasks(task_dict, local_path)
        Writes the working task_dictionary to the appropriate file
        :type local_path: file path
        """
        with open(local_path, 'w') as fp:
            for linenum in sorted(task_dict):
                fp.write("{}{}".format(task_dict[linenum].strip(), os.linesep))
        return TASK_OK, "{:d} Tasks written".format(len(task_dict))
    
    
    def run_hooks(self, func_name, c, p, s, e, t, o, j, x):
        ok = TASK_OK
        msg = ""
        for plugin in self.manager.getAllPlugins():
            if not plugin.is_activated:
                continue
            if hasattr(plugin.plugin_object, func_name):
                logging.getLogger('hooks').debug('Calling %s.%s', plugin.name, func_name)
                func = getattr(plugin.plugin_object, func_name)
                ok, msg, c, p, s, e, t = func(c, p, s, e, t, o, j, x)
        return ok, msg, c, p, s, e, t
    
    
    def add_task(self, text):
        stuff = self.parse_task(text)
        c, p, s, e, t, o, j, x = stuff
        if c and not e:
            e = datetime.datetime.now()
        # run hooks, say, if there is a pend extension, check that the pend id is a valid ID
        err, msg, c, p, s, e, t = self.run_hooks('add_task', c, p, s, e, t, o, j, x)
        if err:
            return err, msg
    
        new_task = self.graft(c, p, s, e, t)
    
        with open(self.config['Files']['task-path'], 'a') as fp:
            fp.write('{}{}'.format(new_task.strip(), os.linesep))
        return TASK_OK, new_task
    

    def add_done(self, text):
        """Adds a completed task. Uses the entry time as start and close
        :param text: Text of the completed task
        """
        c, p, s, e, t, o, j, x = self.parse_task(text)
        if not e:
            e = datetime.datetime.now()
        err, msg, c, p, s, e, t = self.run_hooks('add_task', c, p, s, e, t, o, j, x)
        if err:
            return err, msg
    
        c = True
    
        err, msg, c, p, s, e, t = self.run_hooks('complete_task', c, p, s, e, t, o, j, x)
        if not err:
            return err, msg
    
        done = self.graft(c, p, s, e, t)
        with open(self.config['Files']['task-path'], 'a') as fp:
            fp.write('{}{}'.format(done.strip(), os.linesep))
        return TASK_OK, done    
    
    
    def complete_task(self, tasknum, comment=None):
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].startswith('x'):
            return TASK_ERROR, "Task already completed"
        c, p, s, e, t, o, j, x = self.parse_task(tasks[tasknum])
        c = True
        e = datetime.datetime.now()
        if comment:
            t += " # {}".format(comment)
        tasks[tasknum] = self.graft(c, p, s, e, t)
        # run hooks - anything that should happen in response (grab next item in queue)
        #tasks = _update_pending(tasks, x['uid']) # turn into plugin
        err, msg, c, p, s, e, t = self.run_hooks('complete_task', c, p, s, e, t, o, j, x)
        if err:
            return err, msg
        # End hooks
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, tasks[tasknum]
        



    def sort_tasks(self, by_pri=True, filters=None, filterop=None, showcomplete=None):
        """sort_tasks([by_pri, filters, filteropp, showcomplete])
        Returns a list of (line, task) tuples.
        Default behavior sorts by priority.
        Default behavior does no filtering.-
        Default filter operation is all (all must match).
        Default behavior does not list completed tasks
        Default behavior does not look in the done.txt file.
        To filter, provide a list of strings to filter by.
        """
        # by_pri = by_pri or True # or logic doesn't work when default is true
        filters = filters or []
        filterop = filterop if filterop in (all, any) else all
        if filterop not in (any, all):
            return TASK_ERROR, "Filter Operation must by any or all"
        showcomplete = showcomplete or False
    
        everything = [(key, val) for key, val in list(self.get_tasks(self.config['Files']['task-path']).items())
                      if (showcomplete or not val.startswith('x'))]
    
        if filters:
            everything = [(key, val) for key, val in everything
                          if filterop([_ in val for _ in filters])]
    
        # everything has all open tasks if showcomplete is false.
        # todo .. print completed tasks in revers Cron order? The priorities get wiped
        if by_pri:
            stuff = sorted(everything, key=second)
        else:
            stuff = sorted(everything, key=first)
        return stuff

    
    
    def list_tasks(self, by_pri=True, filters: str = None, filterop=None, showcomplete=None,
                   showext=None):
        """list_tasks([by_pri, filters, filterop, showcomplete, showuid)
        Displays a list of tasks.
        :type by_pri: Boolean
        :param by_pri: If true, sorts by priority, if false, sorts by order in file
        :param filters: Words to filter the list
        :param filterop: all or any (the functions, not strings
        :param showcomplete: If true, shows completed tasks
        :param showuid: If true, shows the Unique ID of the task.
        :rtype: None
        """
        showext = showext or False
        count = 0
        shown_tasks = self.sort_tasks(by_pri, filters, filterop, showcomplete)
    
        for ext in self.config['Tasker']['hidden_extensions'].split(','):
            if ext not in self.extension_hiders:
                self.extension_hiders[ext] = re.compile(r"\s{%s:[^}]*}" % ext.strip())
            
        
        if shown_tasks:
            maxid = max([a for a, b in shown_tasks])
            idlen = len(str(maxid))
            for idx, task in shown_tasks:
                if not showext:
                    for ext in self.extension_hiders:
                        task = self.extension_hiders[ext].sub("", task)
                print(("{1:{0}d} {2}".format(idlen, idx, task)))
                count += 1
            print('-'*(idlen+1))
        msg=("{:d} tasks shown".format(count))
        print(msg)
        return TASK_OK, msg
        
    def prioritize_task(self, tasknum, priority, note=None):
        """prioritize_task(tasknum, new_pri [,note]
        
        Change the priority of a task. Will do nothing if task is closed.
        New priority must be A-W.
        
        :param int tasknum: Number of task to update
        :param str priority: New priority character
        :param str note: Optional note to append 
        """
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].startswith('x '):
            self.log.error('Task %s already completed', tasknum)
            return TASK_ERROR, "Task already completed"
        
        t = self.reprioritize_text(tasks[tasknum], priority)  # reprioritize grafts result
        if note:
            t = re_note.sub('', t)
            t = '%s # %s' % (t, note.strip())
        tasks[tasknum] = t
        self.write_tasks(tasks, self.config['Files']['task-path'])
        return TASK_OK, tasks[tasknum]
        
    def reprioritize_text(self, text, priority):
        """reprioritize(text, new_priority)
        """
        if text.startswith('x '):
            self.log.warn("Cannot reprioritize completed task")
            return text
    
        np = priority.strip()
        match = re.match(r'^[A-W]$', np)
        if not match:
            self.log.error("New priority must be A-W")
            return text
        
        c, p, s, e, t, o, j, x = self.parse_task(text)
        newtext = self.graft(c, match.group(), s, e, t)
        self.log.info("Reprioritized task: %s", newtext)
    
        return newtext