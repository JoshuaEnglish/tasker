"""tasker
Generalized text-only to-do list

Functions with regular names should return a code and a message
Functions beginning with underlines should return task dictionaries
"""

import sys
import os
import datetime
import re
from operator import itemgetter
import configparser
import argparse

import yapsy.ConfigurablePluginManager

import minioncmd
import basetaskerplugin

config = configparser.ConfigParser()
config.read_dict({'Files': {'tasker-dir': os.path.join(os.environ['APPDATA'], 'tasker'),
                            'task-path': "%(tasker-dir)s/todo.txt",
                            'done-path': "%(tasker-dir)s/done.txt",
                            }})

if hasattr(sys, "frozen"):
    configdir = os.path.dirname(sys.executable)
else:
    configdir = os.path.dirname(__file__)

configpath = os.path.join(configdir, 'tasker.ini')

config.read(configpath)

FILES = config['Files']

class TaskCmd(minioncmd.BossCmd):
    prompt = "tasker> "

    def do_list(self, line):
        args = list_parser.parse_args(line.split())
        print(args)
        print(list_tasks(**vars(args)))

    def do_add(self, line):
        args = add_parser.parse_args(line.split())
        print(args)
        print(add_task(" ".join(args.text)))


manager = yapsy.ConfigurablePluginManager.ConfigurablePluginManager(config)
manager.setPluginPlaces(["tasker_plugins", ])
manager.setCategoriesFilter({
    "NewCommand": basetaskerplugin.NewCommandPlugin,
    "SubCommand": basetaskerplugin.SubCommandPlugin,
    "Generic": basetaskerplugin.TaskerPlugin,
})

# collectPlugins automatically loads plugins configured to load
manager.collectPlugins()


TODO = """ Allow for keywords in text like TODAY or NOW or SHORTDATE to
automatically add the current date and/or time in notes or text

Allow quick deletion of extensions (such as note) or absolute replacement
of a note extension.
"""

TASK_OK = 0
TASK_ERROR = 1
TASK_EXTENSION_ERROR = 2

if not os.path.exists(FILES['tasker-dir']):
    os.mkdir(FILES['tasker-dir'])

for path in ['task-path', 'done-path']:
    if not os.path.exists(FILES[path]):
        fd = open(FILES[path], 'w')
        fd.close()

parser = argparse.ArgumentParser('tasker')
commands = parser.add_subparsers(title='commands',
                                 dest="command",
                                 help="supported commands",
                                 )
parser.add_argument('-i', '--interactive', '-l', '--loop', dest="interact",
                    action='store_true', default=False)

list_parser = commands.add_parser('list', help='list tasks')
list_parser.add_argument('-n', action="store_false",
                         dest="by_pri", default=True,
                         help="Prints task list in numerical order, otherwise orders by priority")
list_parser.add_argument('-f', dest="filters", nargs="*",
                         help="Only lists tasks containing these words")
list_parser.add_argument('-y', dest="filterop", action="store_true",
                         default=False,
                         help="Shows tasks matching any filter word. Default is to match all")
list_parser.add_argument('-a', dest="showcomplete", action="store_true", default=False,
                         help="Show completed (but not archived) tasks.")
list_parser.add_argument('-u', dest="showuid", action="store_true", default=False,
                         help="Shows the unique ID of each task")

add_parser =commands.add_parser('add', help="add a task")
add_parser.add_argument(nargs="+", dest="text",
                        help="text of the new task")

do_parser = commands.add_parser('do', help="mark a task as complete")
do_parser.add_argument('tasknum', type=int,
                       help="number of the task to complete")
do_parser.add_argument('comment', nargs=argparse.REMAINDER,
                       help="comment to add to the completed task")


TIMEFMT = '%Y-%m-%dT%H:%M:%S'
IDFMT = '%H%M%S%d%m%y'

re_task = re.compile(
    r"(?P<complete>x\s)?"
    r"(?P<priority>[(][A-Z][)]\s)?"
    r"(?P<start>\d{4}-\d{2}-\d{2}-\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<end>\d{4}-\d{2}-\d{2}-\d{2}:\d{2}:\d{2}\s)?"
    r"(?P<text>.*)"
)

re_context = re.compile("\s([@][-\w]+)")
re_project = re.compile("\s([+][-\w]+)")

re_ext = re.compile(r"\s{\w+:[^}]*}")
re_uid = re.compile(r"\s{uid:[^}]*}")
re_pend = re.compile(r"\s{pend:([^}]*)}")
re_note = re.compile(r"\s{note:([^}]*)}")


def parse_task(text):
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


def graft(complete, priority, start, end, text):
    """Return a single line of text representing the task.
    Does not append a line return
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


def get_tasks(path):
    """Returns a dictionary of (line number (starting at 1), task text) pairs
    """
    res = {}
    with open(path, 'r') as fp:
        idx = 1
        for line in fp.readlines():
            if line.strip():
                res[idx] = line.strip()
                idx += 1
    return res


def write_tasks(task_dict, local_path):
    """write_tasks(task_dict, local_path)
    Writes the working task_dictionary to the appropriate file
    :type local_path: file path
    """
    with open(local_path, 'w') as fp:
        for linenum in sorted(task_dict):
            fp.write("{}{}".format(task_dict[linenum].strip(), os.linesep))
    return TASK_OK, "{:d} Tasks written".format(len(task_dict))


def run_hooks(func_name, c, p, s, e, t, o, j, x):
    ok = TASK_OK
    msg = ""
    for plugin in manager.getAllPlugins():
        if hasattr(plugin.plugin_object, func_name):
            func = getattr(plugin.plugin_object, func_name)
            ok, msg, c, p, s, e, t = func(c, p, s, e, t, o, j, x)
    return ok, msg, c, p, s, e, t


def add_task(text):
    stuff = parse_task(text)
    c, p, s, e, t, o, j, x = stuff
    print(stuff)
    if c and not e:
        e = datetime.datetime.now()
    # run hooks, say, if there is a pend extension, check that the pend id is a valid ID
    err, msg, c, p, s, e, t = run_hooks('add_task', c, p, s, e, t, o, j, x)
    if err:
        return err, msg
    print(c,p,s,e,t, sep=":")
    new_task = graft(c, p, s, e, t)

    with open(FILES['task-path'], 'a') as fp:
        fp.write('{}{}'.format(new_task.strip(), os.linesep))
    return TASK_OK, new_task


def add_done(text):
    """Adds a completed task. Uses the entry time as start and close
    :param text: Text of the completed task
    """
    c, p, s, e, t, o, j, x = parse_task(text)
    if not e:
        e = datetime.datetime.now()
    err, msg, c, p, s, e, t = run_hooks('add_task', c, p, s, e, t, o, j, x)
    if err:
        return err, msg

    c = True

    err, msg, c, p, s, e, t = run_hooks('complete_task', c, p, s, e, t, o, j, x)
    if not err:
        return err, msg

    done = graft(c, p, s, e, t)
    with open(FILES['task-path'], 'a') as fp:
        fp.write('{}{}'.format(done, os.linesep))
    return TASK_OK, done


def _reprioritize(text, new_priority):
    """reprioritize(text, new_priority)
    """
    if text.startswith('x '):
        print("Cannot reprioritize completed task")
        return text

    np = new_priority.strip()
    if not np.isupper():
        print("New priority must be A-X")
        return text
    if len(np) > 1:
        print("New priority must be a single letter")
        return text

    c, p, s, e, t, o, j, x = parse_task(text)
    newtext = graft(c, np, s, e, t)
    print(("Reprioritized task:", newtext))

    return newtext


def _update_pending(tasks, uid):
    """update_pending(tasks, uid)
    Any tasks with a pend extension that matches the uid
    will be given an A priority.

    Question: should the pend extension be erased?
    Answer: NO. Leaving it can allow for task chains to be created a tracked
    :param tasks: dictionary of tasks
    :param uid: uid of recently completed task
    :return:
    """
    tv = tasks.items()
    for idx, text in tv:
        match = re_pend.search(text)
        if match:
            if match.group(1) == uid:
                tasks[idx] = _reprioritize(text, 'A')

    return tasks


def complete_task(tasknum, comment=None):
    tasks = get_tasks(FILES['task-path'])
    if tasknum not in tasks:
        return TASK_ERROR, "Task number not in task list"
    if tasks[tasknum].startswith('x'):
        return TASK_ERROR, "Task already completed"
    c, p, s, e, t, o, j, x = parse_task(tasks[tasknum])
    c = True
    e = datetime.datetime.now()
    if comment:
        t += " # {}".format(comment)
    tasks[tasknum] = graft(c, p, s, e, t)
    # run hooks - anything that should happen in response (grab next item in queue)
    tasks = _update_pending(tasks, x['uid'])
    err, msg, c, p, s, e, t = run_hooks('complete_task', c, p, s, e, t, o, j, x)
    if err:
        return err, msg
    # End hooks
    write_tasks(tasks, FILES['task-path'])
    return TASK_OK, tasks[tasknum]


def add_note(tasknum, note):
    tasks = get_tasks(FILES['task-path'])
    if tasknum not in tasks:
        return TASK_ERROR, "Task number not in task list"
    if tasks[tasknum].startswith('x'):
        return TASK_ERROR, "Task already completed"
    c, p, s, e, t, o, j, x = parse_task(tasks[tasknum])

    # remove old notes
    t = re_note.sub("", t, 1)
    t += " {note: %s}" % note
    tasks[tasknum] = graft(c, p, s, e, t)

    write_tasks(tasks, FILES['task-path'])

    return TASK_OK, tasks[tasknum]


def prioritize(tasknum, new_pri, note=None):
    tasks = get_tasks(FILES['task-path'])
    if tasknum not in tasks:
        return TASK_ERROR, "Task number not in task list"
    if tasks[tasknum].startswith('x'):
        return TASK_ERROR, "Task already completed"
    c, p, s, e, t, o, j, x = parse_task(tasks[tasknum])
    t = _reprioritize(t, new_pri)  # reprioritize grafts result
    tasks[tasknum] = t
    write_tasks(tasks, FILES['task-path'])
    return TASK_OK, tasks[tasknum]


def replace_string_in_task(tasknum, old, new):
    """tasknum - taks to be edited
    old - string to be replaced
    new - string to replace
    """
    tasks = get_tasks(FILES['task-path'])
    if tasknum not in tasks:
        return TASK_ERROR, "Task number not in task list"
    c, p, s, e, t, o, j, x = parse_task(tasks[tasknum])
    t = t.replace(old, new)
    tasks[tasknum] = graft(c, p, s, e, t)
    write_tasks(tasks, FILES['task-path'])
    return TASK_OK, tasks[tasknum]


def delete_note(tasknum):
    """Delete the note extension
    :param tasknum: number of the task to delete the note extension
    """
    tasks = get_tasks(FILES['task-path'])
    if tasknum not in tasks:
        return TASK_ERROR, "Task number not in task list"
    c, p, s, e, t, o, j, x = parse_task(tasks[tasknum])
    t = re_note.sub("", t, 1)
    tasks[tasknum] = graft(c, p, s, e, t)
    write_tasks(tasks, FILES['task-path'])
    return TASK_OK, tasks[tasknum]


first = itemgetter(0)
second = itemgetter(1)


def _sort_tasks(by_pri=True, filters=None, filterop=None, showcomplete=None):
    """_sort_tasks([by_pri, filters, filteropp, showcomplete])
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

    everything = [(key, val) for key, val in list(get_tasks(FILES['task-path']).items())
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


def list_tasks(by_pri=True, filters: str = None, filterop=None, showcomplete=None,
               showuid=None):
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
    showuid = showuid or False
    count = 0
    shown_tasks = _sort_tasks(by_pri, filters, filterop, showcomplete)
    if shown_tasks:
        maxid = max([a for a, b in shown_tasks])
        idlen = len(str(maxid))
        for idx, task in shown_tasks:
            if not showuid:
                task = re_uid.sub("", task)
            print(("{1:{0}d} {2}".format(idlen, idx, task)))
            count += 1
    msg=("{:d} tasks shown".format(count))
    print(msg)
    return TASK_OK, msg


def filter_tasks(filterstring, filterop=None, showcomplete=None):
    """filter_tasks(filterstring [, filterop, showcomplete])
    Prints tasks.

    :param filterstring: string of words to search for
    :param filterop: all or any
    :param showcomplete: if true, will show completed (but not archived) tasks
    :return: None
    """
    list_tasks(filters=filterstring.split(), filterop=filterop, showcomplete=showcomplete)


def do_after(tasknum, new_task_text):
    """do_after(num, text)
    Create a new task with priority Z that is pending completion of a given
    task number.
    Keeps all projects and contexts and extensions except uid (will be given
    uid) and pend (updated to tasknum's uid)
    """
    tasks = get_tasks(FILES['task-path'])
    source_stuff = parse_task(tasks[tasknum])
    # lessee, no worries doing afters if the source is closed.
    # not true. If the original action is closed, this should be
    # an open task. Therefore, raise an error? No. Because user
    # may still want to copy the extensions and projects

    for context in source_stuff[5]:
        if context not in new_task_text:
            new_task_text += " {}".format(context)
    for project in source_stuff[6]:
        if project not in new_task_text:
            new_task_text += " {}".format(project)

    for ext, val in list(source_stuff[7].items()):
        if ext in ['pend', 'uid']:
            continue
        if "{%s:" % ext not in new_task_text:
            new_task_text += " {%s:%s}" % (ext, val)
        else:
            new_task_text = re.sub(r"{%s:([^}]*)}" % ext,
                                   r"{%s:%s}" % (ext, val),
                                   new_task_text)
    new_task_text += " {pend:%s}" % source_stuff[7]['uid']

    new_stuff = parse_task(new_task_text)
    # parse to separate completed and priority - new task should be open and priority Z
    # unless the original task is closed
    new_pri = new_stuff[1] if source_stuff[0] else 'Z'

    # assigns new uid
    return add_task(graft(False, new_pri, *new_stuff[2:5]))


def context_report():
    """Print a list of contexts, noting number of open and closed tasks."""
    contexts = {"NO CONTEXT": {'open': 0, 'closed': 0}}
    tasks = get_tasks(FILES['task-path'])
    for task in list(tasks.values()):
        c, p, s, e, t, o, j, x = parse_task(task)
        if not o:
            if c:
                contexts["NO CONTEXT"]['closed'] += 1
            else:
                contexts["NO CONTEXT"]['open'] += 1
        for context in o:
            if context not in contexts:
                contexts[context] = {'open': 0, 'closed': 0}
            if c:
                contexts[context]['closed'] += 1
            else:
                contexts[context]['open'] += 1
    print("Context, open, closed")
    for context in sorted(contexts):
        if contexts[context]['open']:
            print((context, contexts[context]['open'], contexts[context]['closed']))


def _get_project_counts():
    """Generate a dictionary of dictionaries showing project counts"""
    projects = {}
    tasks = get_tasks(FILES['task-path'])
    for task in list(tasks.values()):
        c, p, s, e, t, o, j, x = parse_task(task)
        for project in j:
            if project not in projects:
                projects[project] = {'open': 0, 'closed': 0}
            if c:
                projects[project]['closed'] += 1
            else:
                projects[project]['open'] += 1
    return projects


def project_report():
    """Print a list of project, noting number of open and closed tasks."""

    print("Project, open, closed")
    projects = _get_project_counts()
    for project in sorted(projects):
        if projects[project]['open']:
            print((project, projects[project]['open'], projects[project]['closed']))


def closed_projects():
    """Print a list of projects with no open tasks"""
    print("Closed Projects")
    projects = _get_project_counts()
    for project in sorted(projects):
        if projects[project]['open'] == 0:
            print((project, projects[project]['closed']))
    if not projects:
        print("None")


def archive_by_project(project):
    """Remove tasks from the main list by project"""
    tasks = get_tasks(FILES['task-path'])
    done = get_tasks(FILES['done-path'])
    print(("Number of Tasks:", len(tasks)))
    print(("Number of Archived Tasks:", len(done)))

    try:
        next_done = max(done) + 1
    except ValueError:
        next_done = 1

    archived_task_keys = []

    for key in tasks:
        c, p, s, e, t, o, j, x = parse_task(tasks[key])
        if project in j:
            print((c, p, s, e, t))
            archived_task_keys.append(key)
            if not c:
                return TASK_ERROR, "Cannot Archive Project - open tasks exist"

    for key in archived_task_keys:
        done[next_done] = tasks[key]
        next_done += 1
        tasks.pop(key)

    print("Post Archive")
    print(("Number of Tasks:", len(tasks)))
    print(("Number of Archived Tasks:", len(done)))

    write_tasks(tasks, FILES['task-path'])
    write_tasks(done, FILES['done-path'])


def archive_closed_projects():
    """archive_closed_projects()
    Remove tasks from the main list by project if the projects are old enough"""

    tasks = get_tasks(FILES['task-path'])
    done = get_tasks(FILES['done-path'])
    print(("Number of Tasks:", len(tasks)))
    print(("Number of Archived Tasks:", len(done)))
    projects = _get_project_counts()

    try:
        next_done = max(done) + 1
    except ValueError:
        next_done = 1

    archived_task_keys = []
    now = datetime.datetime.now()

    for project in projects:
        ok_to_archive = True
        project_tasks = []
        if projects[project]['open'] == 0:
            print(project)

            for item in _sort_tasks(filters=[project, ], showcomplete=True):
                key, line = item
                c, p, s, e, t, o, j, x = parse_task(line)
                print((key, t))
                print(("\t", e, "(%s)" % (now - e)))
                project_tasks.append(key)
                if (now - e).days <= 3:
                    ok_to_archive = False

            if ok_to_archive:
                print("Safe to archive")
                archived_task_keys.extend(project_tasks)
            else:
                print("Too early to archive")

            print()
    # use set to remove duplicates. Some tasks have multiple projects.
    # This can lead to the same task being removed twice.
    for key in set(archived_task_keys):
        done[next_done] = tasks[key]
        next_done += 1
        tasks.pop(key)

    print("Post Archive")
    print(("Number of Tasks:", len(tasks)))
    print(("Number of Archived Tasks:", len(done)))

    write_tasks(tasks, FILES['task-path'])
    write_tasks(done, FILES['done-path'])


def find(stuff):
    """find(stuff)
    Displays a list of tasks. Shortcut for list_tasks(True, stuff, any, True, False)

    :type stuff: string
    :param stuff: string
    :return: None
    """
    return list_tasks(by_pri=True,
                      filters=[item.strip() for item in stuff.split()],
                      filterop=any,
                      showcomplete=True,
                      showuid=False)




c = TaskCmd()

if __name__ == '__main__':
    import sys
    args = parser.parse_args(sys.argv[1:])
    if args.interact:
        c.cmdloop()
    elif not args.command:
        c.onecmd('list')
    else:
        c.onecmd(' '.join(sys.argv[1:]))

    with open(configpath,'w') as fp:
        config.write(fp)