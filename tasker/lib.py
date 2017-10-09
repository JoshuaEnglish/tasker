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

from operator import itemgetter, attrgetter
from collections import defaultdict, Counter
from functools import partial

import colorama
from theme import get_color as get_theme_color

__version__ = "1.6.dev"
__updated__ = "2017-09-29"
__history__ = """
1.1 listing tasks is now case insensitive
1.2 Filtering by (p) matches against the priority
1.3 Fixed bug where notes added in TaskLib.prioritize_task were added as
    a list, not as a string.
1.4 Changed theme to an option to support multiple themes
1.5 Fixed bug where list -c failed
1.6 Added Show Task Hook to allow plugins to refine filtering of tasks
"""


TIMEFMT = '%Y-%m-%dT%H:%M:%S'
IDFMT = '%H%M%S%d%m%y'
DATEFMT = '%Y-%m-%d'

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
re_hide = re.compile(r"\s{hide:(\d{4}-\d{2}-\d{2})}")
re_note = re.compile('\s#\s.*$')

re_pri_filter = re.compile(r"~?\(([A-Z])\)")

TASK_OK = 0
TASK_ERROR = 1
TASK_EXTENSION_ERROR = 2

re_color = re.compile("""
(?P<style>bright|dim|normal)\s
(?P<fore>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow)\s
on\s(?P<back>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow)
""", re.VERBOSE + re.IGNORECASE)


# todo: add note as a slot for further processing
class Task(object):
    """Simple container for parsed tasks"""

    __slots__ = ('complete', 'priority', 'start', 'end', 'text',
                 'contexts', 'projects', 'extensions')

    def __init__(self, complete, priority, start, end, text,
                 contexts, projects, extensions):
        self.complete = complete
        self.priority = priority
        self.start = start
        self.end = end
        self.text = text
        self.contexts = contexts
        self.projects = projects
        self.extensions = extensions

    def __str__(self):
        res = []
        if self.complete:
            res.append('x')
        if self.priority and not self.complete:
            res.append('(%s)' % self.priority)
        if self.start:
            res.append(self.start.strftime(TIMEFMT))
        if self.end:
            res.append(self.end.strftime(TIMEFMT))
        res.append(self.text.strip())
        return " ".join(res)

    # __contains__ allows for filtering tasks by content
    def __contains__(self, searchtext):
        return searchtext.lower() in self.text.lower()

    # __lt__ is required for sorting tasks
    def __lt__(self, other):
        return str(self) < str(other)

    @classmethod
    def from_text(cls, text):
        """from_text(text)
        Returns a parsed task from a line of text.
        If text starts with *x* and no end time is given, current time
        will be used as end time.
        """
        text = text.strip()
        match = re_task.match(text)
        if not any(match.groups()):
            raise ValueError('Task did not parse')
        complete = bool(match.group('complete'))

        priority = match.group('priority')[1] if match.group('priority') else ''

        if match.group('start'):
            start = datetime.datetime.strptime(match.group('start').strip(),
                                               TIMEFMT)
        else:
            start = datetime.datetime.now()

        if match.group('end'):
            end = datetime.datetime.strptime(match.group('end').strip(),
                                             TIMEFMT)
        else:
            end = None

        if complete and not end:
            end = datetime.datetime.now()

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

        return cls(complete, priority, start, end, task,
                   context, projects, edict)


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

        self.theme = {}

    def set_theme(self, theme_name=False):

        if not theme_name:
            return
        theme_name = theme_name.title()

        if theme_name == 'None':
            self.theme = {}
            return

        config_name = 'Theme: {}'.format(theme_name)
        if self.config.has_section(config_name):
            self.log.info("Setting '%s' color theme", theme_name)
            self.theme = dict((k.title(), get_theme_color(v)) for k, v in
                              self.config.items(config_name))
        else:
            self.log.info("Setting default color theme")
            self.theme = {
                "A": colorama.Fore.RED + colorama.Style.BRIGHT,
                "B": colorama.Fore.YELLOW,
                "C": colorama.Fore.GREEN,
                "P": colorama.Fore.CYAN + colorama.Style.BRIGHT,
                "Z": colorama.Fore.LIGHTBLACK_EX
                }

    def get_extensions_to_hide(self):
        """get_extensions_to_hide()
        Compile a list of all extensions from the config file
        """
        ext_list = ','.join([self.config[section].get('hidden-extensions', '')
                             for section in self.config])
        ext_list = [ext.strip() for ext in ext_list.split(',') if ext]
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
        """Deprecated. No longer implemented. This method exists
        just to catch old code.
        """
        raise NotImplementedError("Please use the task object from here on out")

    def graft(self, complete, priority, start, end, text):
        """Deprecated. No longer implemented. This method exists
        just to catch old code.
        """
        raise NotImplementedError("Please use the Task object from here on out")

    def get_tasks(self, path):
        """Get tasks from either todo.txt or done.txt

        :param path: path to the file to read
        :rtype: dict
        :return: dictionary of line number, task instance pairs
        """
        res = {}
        with open(path, 'r') as fp:
            idx = 1
            for line in fp.readlines():
                if line.strip():
                    res[idx] = Task.from_text(line.strip())
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
                fp.write("{}{}".format(task_dict[linenum], '\n'))
        return TASK_OK, "{:d} Tasks written".format(len(task_dict))

    def run_hooks(self, func_name, this):
        ok = TASK_OK
        msg = ""
        for plugin in self.manager.getAllPlugins():
            if not plugin.is_activated:
                continue
            if hasattr(plugin.plugin_object, func_name):
                logging.getLogger('hooks').debug('Calling %s.%s',
                                                 plugin.name, func_name)
                func = getattr(plugin.plugin_object, func_name)
                ok, msg, this = func(this)
        return ok, msg, this

    def add_task(self, text):
        this = Task.from_text(text)

        # if c and not e:
        #     e = datetime.datetime.now()

        err, msg, this = self.run_hooks('add_task', this)
        if err:
            self.log.error(msg)
            return err, msg

        with open(self.config['Files']['task-path'], 'a') as fp:
            fp.write('{}{}'.format(this, '\n'))
        print(this)
        return TASK_OK, str(this)

    def add_done(self, text):
        """Adds a completed task. Uses the entry time as start and close
        :param text: Text of the completed task

        Depracated: Use ``t add x ...`` in the CLI. If a task text begins with
        ``x `` then the task will be created as closed
        """
        raise NotImplementedError("If you get this, something has gone wrong.")

    def complete_task(self, tasknum, comment=None):
        """Completes an open task if task is not already closed.
        """
        # Check if self.tasks has been established
        if not hasattr(self, 'tasks') or self.tasks is None:
            tasks = self.tasks = self.get_tasks(
                self.config['Files']['task-path'])
        else:
            tasks = self.tasks

        if tasknum not in tasks:
            del self.tasks
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            del self.tasks
            return TASK_ERROR, "Task already completed"

        this = tasks[tasknum]
        this.complete = True
        this.end = datetime.datetime.now()
        if comment:
            this.text += " # {}".format(comment)
        tasks[tasknum] = this

        err, msg, this = self.run_hooks('complete_task', this)
        if err:
            return err, msg
        # End hooks
        self.write_tasks(tasks, self.config['Files']['task-path'])
        del self.tasks
        print(tasks[tasknum])
        return TASK_OK, tasks[tasknum]

    def sort_tasks(self, by_pri=True, filters=None, filterop=None,
                   showcomplete=None, opendate=None, closedate=None,
                   hidedate=None):
        """sort_tasks([by_pri, filters, filteropp, showcomplete])
        Returns a list of (line, task) tuples.
        Default behavior sorts by priority.
        Default behavior does no filtering.
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
        showcomplete = showcomplete or closedate or False
        hidedate = hidedate or datetime.date.today()

        everything = [(key, val)
                      for key, val in list(self.get_tasks(
                          self.config['Files']['task-path']).items())
                      if (showcomplete or not val.complete)]

        if filters:
            self.log.info('Filtering tasks by keywords')

            def include_task(filters, task):
                "return a boolean value to include the task or not"
                yeas = []
                for word in filters:
                    # yea = False
                    yea = word.startswith('~')
                    testword = word.replace('~', '').lower()
                    if testword in task.text.lower():
                        # yea = True
                        yea = not yea
                    pri = re_pri_filter.match(word)
                    if pri and pri.group(1) == task.priority:
                        yea = not yea
                    yeas.append(yea)
                return filterop(yeas)

            everything = [(key, val) for key, val in everything
                          if include_task(filters, val)]

        if not self.config['Tasker'].getboolean('show-priority-z', True):
            self.log.info("Hiding priority Z tasks")
            everything = [(key, val) for key, val in everything
                          if val.priority != "Z"]

        if opendate:
            self.log.info("Showing items opened on %s", opendate)
            everything = [(key, val) for key, val in everything
                          if val.start.date() == opendate]

        if closedate:
            self.log.info("Showing items closed on %s", closedate)
            everything = [(key, val) for key, val in everything
                          if val.end and val.end.date() == closedate]

        # if the task has a hide extension and the value of that extension
        # is greater than the current day, do not show task.

        # show task unless there is a hide extension and the value is greater
        # than the current day

        everything = [(key, task) for key, task in everything
                      if datetime.datetime.strptime(
                          task.extensions.get('hide',
                                              hidedate.strftime(DATEFMT)),
                          DATEFMT).date() <= hidedate]

        if by_pri:
            plist, zlist, ulist = [], [], []
            for key, val in everything:
                pri = val.priority
                if pri and pri != 'Z':
                    plist.append((key, val))
                elif not pri:
                    ulist.append((key, val))
                else:
                    zlist.append((key, val))

            getter = itemgetter(1)
            if self.config['Tasker'].getboolean('priority-z-last', True):
                stuff = (sorted(plist, key=getter) +
                         sorted(ulist, key=getter) +
                         sorted(zlist, key=getter))
            else:
                stuff = (sorted(plist, key=getter) +
                         sorted(zlist, key=getter) +
                         sorted(ulist, key=getter))

        else:
            stuff = sorted(everything, key=itemgetter(0))
        return stuff

    def list_tasks(self, by_pri=True, filters: str = None, filterop=None,
                   showcomplete=None, showext=None,
                   opendate=None, closedate=None, hidedate=None):
        """list_tasks([by_pri, filters, filterop, showcomplete, showuid)
        Displays a list of tasks.
        :type by_pri: Boolean
        :param bool by_pri: If true, sorts by priority,
                       if false, sorts by order in file
        :param str filters: Words to filter the list
        :param func filterop: all or any (the functions, not strings
        :param bool showcomplete: If true, shows completed tasks
        :param bool showext: If true, shows the normally hidden
                             extensions of the task.
        :param date opendate: If not None, filters tasks opened on opendate
        :param date closedate: If not None, filters tasks closed on closedate
        :param date hidedate: The date to filter extensions marked to hide
        :rtype: TASK_OK, None
        """
        showext = showext or False
        count = 0
        # colorize = self.config['Tasker'].getboolean('use-color', True)
        shown_tasks = self.sort_tasks(by_pri, filters, filterop, showcomplete,
                                      opendate, closedate, hidedate)
        self.log.info('Listing %s tasks %s',
                      'all' if showcomplete else 'open',
                      'by priority' if by_pri else 'by number')

        for ext in self.get_extensions_to_hide():
            if ext not in self.extension_hiders:
                self.extension_hiders[ext] = re.compile(r"\s{%s:[^}]*}" % ext)

        wrap_width = self.config['Tasker'].getint('wrap-width', 78)
        if not self._textwrapper:
            self._textwrapper = textwrap.TextWrapper(width=wrap_width)

        if shown_tasks:
            maxid = max([a for a, b in shown_tasks])
            idlen = len(str(maxid))
            self._textwrapper.subsequent_indent = ' ' * (idlen+5)
            wrap = self.config['Tasker'].get('wrap-behavior', 'none')
            wrapfunc = str
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
                pri = task.priority

                if not showext:
                    for ext in self.extension_hiders:
                        task.text = self.extension_hiders[ext].sub("",
                                                                   task.text)
                print(("{3}{1:{0}d} {2}".format(idlen, idx,
                                                wrapfunc(str(task)),
                                                self.get_color(pri))))
                count += 1
            print('{0}{1}'.format(colorama.Fore.RESET, '-'*(idlen+1)))
        msg = ("{:d} task{:s} shown".format(count, '' if count == 1 else 's'))
        print(msg)
        return TASK_OK, msg

    def get_color(self, pri):
        color = self.theme.get(pri, colorama.Style.RESET_ALL)
        self.log.debug('getting color for %s (%s)', pri, color)
        return color

    def note_task(self, tasknum, note=None):
        """Updates the note on a task by task number."""
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        t = tasks[tasknum]
        t.text = self.update_note(t.text, note)
        tasks[tasknum] = t
        self.write_tasks(tasks, self.config['Files']['task-path'])
        print(tasknum, tasks[tasknum])
        return TASK_OK, tasks[tasknum]

    def update_note(self, text, note=None):
        """updates the note from a line of text. If note is None or blank,
        removes the note from the text entirely.
        """
        if note:
            return "{} # {}".format(re_note.sub('', text), note)
        else:
            return re_note.sub('', text)

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
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed', tasknum)
            return TASK_ERROR, "Task already completed"

        t = self.reprioritize_task(tasks[tasknum], priority)
        t.text = self.update_note(t.text, ' '.join(note))
#        if note:
#            text = re_note.sub('', t.text)
#            t.text = '%s # %s' % (text, ' '.join(note).strip())
        tasks[tasknum] = t
        self.write_tasks(tasks, self.config['Files']['task-path'])
        print(tasks[tasknum])
        return TASK_OK, tasks[tasknum]

    def write_current_tasks(self):
        """write the current tasks to the correct file"""
        self.write_tasks(self.tasks, self.config['Files']['task-path'])

    def reprioritize_task(self, task, priority):
        """reprioritize_task(task, new_priority)
        """
        if task.complete:
            self.log.warn("Cannot reprioritize completed task")
            return task

        np = priority.strip()
        match = re.match(r'^[A-Z]$', np)
        if not match:
            self.log.error("New priority must be A-Z")
            return task

        task.priority = match.group()

        self.log.info("Reprioritized task: %s", task)

        return task

    def hide_task(self, tasknum, hidedate):
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed. Cannot hide')
            return TASK_ERROR, "Cannot hide closed task"
        if 'hide' not in tasks[tasknum].extensions:
            tasks[tasknum].text += " {hide:%s}" % hidedate.strftime(DATEFMT)
        else:
            tasks[tasknum].text = re_hide.sub(
                " {hide:%s}" % hidedate.strftime(DATEFMT), tasks[tasknum].text)
        self.write_tasks(tasks, self.config['Files']['task-path'])
        print(tasks[tasknum])
        return TASK_OK, tasks[tasknum]

    def unhide_task(self, tasknum):
        tasks = self.get_tasks(self.config['Files']['task-path'])
        if tasknum not in tasks:
            self.log.error('Task %s not in list', tasknum)
            return TASK_ERROR, "Task number not in task list"
        if tasks[tasknum].complete:
            self.log.error('Task %s already completed. Cannot unhide')
            return TASK_ERROR, "Cannot unhide completed task"
        tasks[tasknum].text = re_hide.sub("", tasks[tasknum].text)
        self.write_tasks(tasks, self.config['Files']['task-path'])
        print(tasks[tasknum])
        return TASK_OK, tasks[tasknum]

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
                    tasks['x%d' % key] = val

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
            getter = attrgetter('projects')
        elif kind == 'CONTEXT':
            getter = attrgetter('contexts')
        else:
            raise ValueError("Should pass 'project' or 'context' to get_counts")
        res = defaultdict(Counter)
        nothing = 'NO {}'.format(kind)

        tasks = self.build_task_dict(include_archive, only_archive)

        for task in tasks.values():
            items = getter(task)  # projects and contexts are lists

            key = 'closed' if task.complete else 'open'

            if not items:
                res[nothing][key] += 1

            for item in items:
                res[item][key] += 1
                res[item][task.priority] += 1

        return res


if __name__ == '__main__':
    task = Task.from_text("x check for approval on +OUMeridianMaps @quote")
    print(task, task.complete)
