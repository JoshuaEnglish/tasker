# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 14:28:15 2016

@author: jenglish
"""
import os
import re
import datetime
import logging
import textwrap

from operator import itemgetter
from collections import defaultdict, Counter
from functools import partial

import colorama


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

        self._textwrapper = None

        
        if not os.path.exists(config['Files']['tasker-dir']):
            try:
                os.mkdir(config['Files']['tasker-dir'])
            except FileNotFoundError:
                self.log.error("Default file not found, resetting")
                config['Files']['tasker-dir'] = os.path.join(
                                                  os.environ['APPDATA'], 
                                                  'tasker')
                if not os.path.exists(config['Files']['tasker-dir']):
                    os.mkdir(config['Files']['tasker-dir'])
                

        for path in ['task-path', 'done-path']:
            if not os.path.exists(config['Files'][path]):
                fd = open(config['Files'][path], 'w')
                fd.close()

        self.theme = {
            "A" : colorama.Fore.RED,
            "B" : colorama.Fore.YELLOW,
            "C" : colorama.Fore.GREEN,
            }
    def get_extensions_to_hide(self):
        """get_extensions_to_hide()
        Compile a list of all extensions from the config file
        """
        ext_list = ','.join([self.config[d].get('hidden-extensions','')
                             for d in self.config])
        ext_list = [s.strip() for s in ext_list.split(',') if s]
        return ext_list

    def hide_extension(self, ext):
        """hide_extension(ext)
        Adds the extension to tasker's list of hidden extensions.
        Hidden extensions will not appear in task lists.
        """
        if not self.config:
            self.log.error('Cannot add hidden extension: No configuration')
            return None

        extensions = self.config['Tasker']['hidden_extensions'].split(',')
        extensions = [e.strip() for e in extensions]
        ext = ext.strip()
        if ext not in extensions:
            extensions.append(ext)

        self.config['Tasker']['hidden_extensions'] = ','.join(extensions)

    def show_extension(self, ext):
        """show_extension(ext)
        Removes the extension from tasker's list of hidden extensions.
        Does not issue an error if the extension is not in the list
        """
        if not self.config:
            self.log.error('Cannot add hidden extension: No configuration')
            return None

        extensions = self.config['Tasker']['hidden_extensions'].split(',')
        extensions = [e.strip() for e in extensions]
        ext = ext.strip()
        if ext in extensions:
            extensions.remove(ext)

        self.config['Tasker']['hidden_extensions'] = ','.join(extensions)

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
          
            :param str text: text of a task.
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
        :param dict task_dict: dictionary of (line: task) pairs
        :param filepath local_path: file path to write to
        """
        self.log.info('Writing tasks to %s', local_path)
        with open(local_path, 'w') as fp:
            for linenum in sorted(task_dict):
                fp.write("{}{}".format(task_dict[linenum].strip(), '\n'))
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

        if c  and not e:
            e = datetime.datetime.now()

        # run hooks, say, if there is a pend extension, check that the pend id is a valid ID
        err, msg, c, p, s, e, t = self.run_hooks('add_task', c, p, s, e, t, o, j, x)
        if err:
            self.log.error(msg)
            return err, msg

        new_task = self.graft(c, p, s, e, t)

        with open(self.config['Files']['task-path'], 'a') as fp:
            fp.write('{}{}'.format(new_task.strip(), '\n'))
        print(new_task)
        return TASK_OK, new_task


    def add_done(self, text):
        """Adds a completed task. Uses the entry time as start and close
        :param text: Text of the completed task
        """
        self.tasks = self.get_tasks(self.config['Files']['task-path'])
        c, p, s, e, t, o, j, x = self.parse_task(text)
        if not e:
            e = datetime.datetime.now()
        err, msg, c, p, s, e, t = self.run_hooks('add_task', c, p, s, e, t, o, j, x)
        if err:
            self.log.error(msg)
            return err, msg

        c = True

        err, msg, c, p, s, e, t = self.run_hooks('complete_task', c, p, s, e, t, o, j, x)
        if err:
            self.log.error(msg)
            return err, msg

        done = self.graft(c, p, s, e, t)
        with open(self.config['Files']['task-path'], 'a') as fp:
            fp.write('{}{}'.format(done.strip(), '\n'))
        del self.tasks
        print(done)
        return TASK_OK, done


    def complete_task(self, tasknum, comment=None):
        """Completes an open task if task is not already closed.
        """
        # Check if self.tasks has been established
        if not hasattr(self, 'tasks') or self.tasks is None:
            tasks = self.tasks = self.get_tasks(self.config['Files']['task-path'])
        else:
            tasks = self.tasks
        if tasknum not in tasks:
            del self.tasks
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].startswith('x'):
            del self.tasks
            return TASK_ERROR, "Task already completed"

        
        c, p, s, e, t, o, j, x = self.parse_task(tasks[tasknum])
        c = True
        e = datetime.datetime.now()
        if comment:
            t += " # {}".format(comment)
        tasks[tasknum] = self.graft(c, p, s, e, t)
        # run hooks - anything that should happen in response (grab next item in queue)

        err, msg, c, p, s, e, t = self.run_hooks('complete_task', c, p, s, e, t, o, j, x)
        if err:
            self.log.error(msg)
            return err, msg
        # End hooks
        self.write_tasks(tasks, self.config['Files']['task-path'])
        del self.tasks
        print(tasks[tasknum])
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

        filters = filters or []
        filterop = filterop if filterop in (all, any) else all
        if filterop not in (any, all):
            self.log.error('Bad filterop parameter in sort_tasks')
            return TASK_ERROR, "Filter Operation must by any or all"
        showcomplete = showcomplete or False

        everything = [(key, val) 
                      for key, val in list(self.get_tasks(
                          self.config['Files']['task-path']).items())
                      if (showcomplete or not val.startswith('x'))]

        if filters:
            self.log.info('Filtering tasks by keywords')
            everything = [(key, val) for key, val in everything
                          if filterop([_ in val for _ in filters])]
        
        if not self.config['Tasker'].getboolean('show-priority-z', True):
            self.log.info("Hiding priority Z tasks")
            everything = [(key, val) for key,val in everything
                          if self.parse_task(val)[1] != "Z"]

        # todo .. print completed tasks in revers Cron order? The priorities get wiped
        if by_pri:
            # break up list into three lists: prioritized, unprioritized, and Z
            plist, zlist, ulist = [],[],[]
            for key,val in everything:
                pri = self.parse_task(val)[1]
                if pri and pri != 'Z':
                    plist.append((key, val))
                elif not pri:
                    ulist.append((key, val))
                else:
                    zlist.append((key, val))

            self.log.debug('plist keys: %s', ','.join(str(a) for a,b in plist))
            self.log.debug('zlist keys: %s', ','.join(str(a) for a,b in zlist))
            self.log.debug('ulist keys: %s', ','.join(str(a) for a,b in ulist))
            
            if self.config['Tasker'].getboolean('priority-z-last', True):
                stuff = (sorted(plist, key=second) + 
                         sorted(ulist, key=second) + 
                         sorted(zlist, key=second))
            else:
                stuff = (sorted(plist, key=second) +
                         sorted(zlist, key=second) +
                         sorted(ulist, key=second))
            
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
        :param showext: If true, shows the normally hidden extensions of the task.
        :rtype: None
        """
        showext = showext or False
        count = 0
        colorize = self.config['Tasker'].getboolean('use-color', True)
        shown_tasks = self.sort_tasks(by_pri, filters, filterop, showcomplete)
        self.log.info('Listing %s tasks %s',
                      'all' if showcomplete else 'open',
                      'by priority' if by_pri else 'by number')

        for ext in self.get_extensions_to_hide():
            if ext not in self.extension_hiders:
                self.extension_hiders[ext] = re.compile(r"\s{%s:[^}]*}" % ext.strip())

        wrap_width = self.config['Tasker'].getint('wrap-width', 78)
        if not self._textwrapper:
            self._textwrapper = textwrap.TextWrapper(width=wrap_width)
            
        if shown_tasks:
            maxid = max([a for a, b in shown_tasks])
            idlen = len(str(maxid))
            self._textwrapper.subsequent_indent = ' '*(idlen+5)
            wrap = self.config['Tasker'].get('wrap-behavior', 'none')
            if wrap == 'wrap':
                self.log.info("Wrapping long lines of each task")
                wrapfunc = self._textwrapper.fill
            elif wrap == 'shorten':
                self.log.info("Shortening each task")
                wrapfunc = partial(textwrap.shorten, width=wrap_width, 
                                   placeholder='...')
            elif wrap == 'none':
                wrapfunc = str
            else:
                self.log.error("Unknown textwrap preference %s", wrap)
            for idx, task in shown_tasks:
                pri = self.parse_task(task)[1]
            
                if not showext:
                    for ext in self.extension_hiders:
                        task = self.extension_hiders[ext].sub("", task)
                print(("{3}{1:{0}d} {2}".format(idlen, idx,
                                                wrapfunc(task),self.get_color(pri))))
                count += 1
            print('-'*(idlen+1))
        msg=("{:d} task{:s} shown".format(count, '' if count==1 else 's'))
        print(msg)
        return TASK_OK, msg

    def get_color(self, pri):
        return self.theme.get(pri, colorama.Fore.RESET)
        
    def prioritize_task(self, tasknum, priority, note=None):
        """prioritize_task(tasknum, new_pri [,note]
        
        Change the priority of a task. Will do nothing if task is closed.
        New priority can be A-Z but should be A-W.
        
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
        print(tasks[tasknum])
        return TASK_OK, tasks[tasknum]

    def reprioritize_text(self, text, priority):
        """reprioritize(text, new_priority)
        """
        if text.startswith('x '):
            self.log.warn("Cannot reprioritize completed task")
            return text

        np = priority.strip()
        match = re.match(r'^[A-Z]$', np)
        if not match:
            self.log.error("New priority must be A-Z")
            return text

        c, p, s, e, t, o, j, x = self.parse_task(text)
        newtext = self.graft(c, match.group(), s, e, t)
        self.log.info("Reprioritized task: %s", newtext)

        return newtext

    def build_task_dict(self, include_archive=False, only_archive=False):
        """build_task_dict(include_archive, only_archive)
        Builds a dictionary of tasks, much like :meth:`get_tasks` but will
        read either file, or both.
        """
        if only_archive:
            tasks = self.get_tasks(self.config['Files']['done-path'])
        else:
            tasks = self.get_tasks(self.config['Files']['task-path'])
            if include_archive:
                done = self.get_tasks(self.config['Files']['done-path'])
                for key, val in done.items():
                    tasks['x%d' % key]=val

        return tasks


    def get_counts(self, kind, include_archive=False, only_archive=False):
        """get_counts(kind, include_archive, only_archive)
        Returns a dictionary of :class:`collections.Counter` objects.
        
        
        :param str kind: 'project' or 'context'
        :param bool include_archive: passed to :meth:`build_task_dict`
        :param bool only_archive: passet to :meth:`build_task_dict`
        
        The resulting dictionary looks like::
            
            {'+SomeProject': Counter({'open': 2, 'closed': 1})}
        
        
        """
        kind = kind.upper()

        if kind == 'PROJECT':
            idx = 6
        elif kind == 'CONTEXT':
            idx = 5
        else:
            raise ValueError("Should pass 'project' or 'context' to get_counts")
        res = defaultdict(Counter)
        nothing = 'NO {}'.format(kind)

        tasks=self.build_task_dict(include_archive, only_archive)

        for task in tasks.values():
            stuff = self.parse_task(task)
            items = stuff[idx] # projects and contexts are lists
            closed = stuff[0]
            key = 'closed' if closed else 'open'

            if not items:
                res[nothing][key] += 1

            for item in items:
                res[item][key] += 1

        return res


