# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 10:29:54 2016

@author: jenglish
"""
from __future__ import absolute_import

import os

import argparse
import datetime
import logging

from . import minioncmd
from . import lister

def add_core_subparsers(commands):
    list_parser = commands.add_parser('list', help='list tasks',
                                      description="Tool for listing tasks",
                                      )
    list_parser.add_argument('-n', action="store_false",
                             dest="by_pri", default=True,
                             help="Prints task list in numerical order, otherwise orders by priority")

    list_parser.add_argument('-y', dest="filterop", action="store_true",
                             default=False,
                             help="Shows tasks matching any filter word. Default is to match all")
    list_parser.add_argument('-a', dest="showcomplete", action="store_true",
                             default=False,
                             help="Show completed (but not archived) tasks.")
    list_parser.add_argument('-x', dest="showext", action="store_true",
                             default=False,
                             help="Shows hidden text extensions")
    list_parser.add_argument('filters', nargs=argparse.REMAINDER,
                             help="Only lists tasks containing these words")

    add_parser = commands.add_parser('add', help="add a task")
    add_parser.add_argument('-d','--done', action="store_true",
                            default=False, help="Adds task as completed")
    add_parser.add_argument(nargs="+", dest="text",
                            help="text of the new task")

    do_parser = commands.add_parser('do', help="mark a task as complete")
    do_parser.add_argument('tasknum', type=int,
                           help="number of the task to complete")
    do_parser.add_argument('comment', nargs=argparse.REMAINDER,
                           help="comment to add to the completed task")

    priority_parser = commands.add_parser('pri', help="prioritize a task")
    priority_parser.add_argument('tasknum', type=int,
                                 help="number of the task to prioritize")
    priority_parser.add_argument('priority', type=str,
                                 help="letter of new priority or _ to clear")
    priority_parser.add_argument('note', nargs=argparse.REMAINDER,
                                 help="optional note to attach to task")

plugin_argparser = argparse.ArgumentParser('plugins')
plugin_commands = plugin_argparser.add_subparsers(title='commands',
                                 dest="command",
                                 help="supported commands")
plugin_commands.add_parser('list', help='List the known plugins')

activate = plugin_commands.add_parser('activate', 
                                      help='Activate plugins by name')
activate.add_argument('name', help='name of the plugin to activate')

deactivate = plugin_commands.add_parser('deactivate', 
                                        help='Deactivate plugin by name')
deactivate.add_argument('name', help='name of the plugin to deactivate')

plugin_commands.add_parser('categories', 
                           help='list current plugin categories')

create = plugin_commands.add_parser('create',
                                    help="Create a new plugin")
create.add_argument('name', help="name of the plugin to template")
create.add_argument('kind', choices=['new', 'sub', 'generic'],
                    help="The kind of plugin to template")

class_map = {'new': 'NewCommandPlugin',
             'sub': 'SubCommandPlugin',
             'generic': 'TaskerPlugin'}


class PluginCmd(minioncmd.MinionCmd):
    """PluginCmd(name [,master, manager, completekey, stdin, stout])
    Specialized subclass of MinionCmd that has access to the YAPSY
    manager.
    """

    prompt = "plugins> "
    doc_leader = "Plugins Help"
    _log = logging.getLogger('plugin')

    def __init__(self, name, master=None, manager=None,
                 completekey='tab', stdin=None, stdout=None):
        self.manager = manager
        super().__init__(name, master, completekey, stdin, stdout)

    def get_plugin_name_and_category(self, name):
        candidates = [info for info in self.manager.getAllPlugins() if
                      info.name == name]
        if not candidates:
            return None, None
        elif len(candidates) > 1:
            return None, None
        else:
            info = candidates[0]
            return info.name, info.category

    def do_list(self, line):
        """Lists all plugins and their categories"""
        lister.print_list([(info.name, info.category, str(info.is_activated))
                           for info in self.manager.getAllPlugins()],
                          "Name Category Activated".split())
        # for info in self.manager.getAllPlugins():
        #     print(info.name, info.category, info.is_activated, sep=", ")

    def do_categories(self, line):
        """Lists all plugin categories"""
        for category in self.manager.getCategories():
            print(category)

    def do_activate(self, line):
        """Activates a plugin by name.
        Plugin will be activated on next launch
        """
        stuff = line.split(maxsplit=1)
        if len(stuff)== 1:
            name, category = self.get_plugin_name_and_category(line)
        else:
            name, category = stuff
        info = self.manager.getPluginByName(name, category)
        if not info:
            name, category = self.get_plugin_name_and_category(name)
        if not name:
            print("No plugin found")
            return None
        else:
            self.manager.activatePluginByName(name, category, True)
            print("Plugin activated. Will be active when program restarts.")

    def do_deactivate(self, line):
        """Deactivates a plugin by name.
        Plugin will be deactivated on next launch.
        """
        stuff = line.split(maxsplit=1)
        if len(stuff)== 1:
            name, category = self.get_plugin_name_and_category(line)
        else:
            name, category = stuff
        info = self.manager.getPluginByName(name, category)
        if not info:
            name, category = self.get_plugin_name_and_category(name)
        if not name:
            print("No plugin found")
            return None
        else:
            self.manager.deactivatePluginByName(name, category, True)
            print("Plugin activated. Will be active when program restarts.")
            
    def do_create(self, line):
        """Creates a template for for a new plugin"""
        args = create.parse_args(line.split())
        args.name = args.name.title()
        args.user = os.environ['USERNAME']
        args.date = datetime.datetime.isoformat(datetime.datetime.now())
        args.lowername = args.name.lower()
        args.cls = class_map[args.kind]
        args.clicode = CLI_CODE.format(**vars(args)) if args.kind=='sub' else ''
        args.clilink = CLI_LINK.format(**vars(args)) if args.kind=='sub' else ''
        folder = os.path.abspath(
                    self.manager.getPluginLocator().plugins_places[0])
        
        def_path = os.path.join(folder, 
                                "{}Plugin.tasker-plugin".format(args.name))
        with open(def_path, 'w') as fp:
            print(PLUGIN_DEFINITION.format(**vars(args)), file=fp, flush=True)
        
        code_path = os.path.join(folder, 
                                 "{}Plugin.py".format(args.name))
        with open(code_path, 'w') as fp:
            print(PLUGIN_CODE.format(**vars(args)), file=fp, flush=True)
            
        print("The files have been written to:")
        print(def_path)
        print(code_path)
            

PLUGIN_DEFINITION = """# Plugin Definition File
# generated by plugins create NAME TYPE
[Core]
Name = {name}
Module = {name}Plugin

[Documentation]
Author = {user}
Version = 0.0
Website = http://example.com
Description = Twiddles its thumbs
"""

CLI_CODE = '''
from tasker import minioncmd

class {name}CLI(minioncmd.MinionCmd):
    prompt = "{lowername}> "

    def __init__(self, completekey='tab', stdin=None, stdout=None, ):
        super().__init__('{lowername}', 
                         completekey=completekey, 
                         stdin=stdin, 
                         stdout=stdout)
        
'''

CLI_LINK = '''
        self.cli_name = '{lowername}'
        self.cli = {name}CLI()
        
        '''
PLUGIN_CODE = '''
"""
{name}Plugin

Twiddles its thumbs

Created on {date}

@author: {user}
"""
import argparse
import basetaskerplugin

{clicode}
class {name}Plugin(basetaskerplugin.{cls}):
    def activate(self):
        self._log.debug('Activating {name}')
        # edit the following line
        self.setConfigOption('public_methods', 'do_{name}')

        {clilink}
        # define argument parsers
        {lowername} = argparse.ArgumentParser('{lowername}')
        
        # add parsers

        self.parsers = {{
            {lowername}: "Thumb twiddlers",            
        }}

        super().activate()

    def do_{name}(self, text):
        """Thumb twiddler"""
        pass

    # hook method - delete if not going to use
    def add_task(self, c, p, s, e, t, o, j, x):
        return (0, "", c, p, s, e, t)
        
    # hook method - delete if not going to use
    def complete_task(self, c, p, s, e, t, o, j, x):
        return (0, "", c, p, s, e, t)

'''

archive_argparser = argparse.ArgumentParser('archive')

archive_commands = archive_argparser.add_subparsers(title='commands',
                                 dest="archivecommand",
                                 metavar="")

archive_parent =argparse.ArgumentParser(add_help=False)
archive_parent.add_argument('--days', type=int, default=3, 
                               help='minimum age of closed tasks to archive')

archive_project_parser = archive_commands.add_parser('project', 
                                                     help='Archive by project',
                                    parents=[archive_parent])

archive_project_parser.add_argument('projects', 
                                    help="names of Projects to archive", 
                                    nargs=argparse.REMAINDER)


class ArchiveCmd(minioncmd.MinionCmd):
    prompt = "archive> "
    doc_leader = """Archive Help
    
    These commands archive tasks by project or number.
    Tasks that are not old enough (set by --days) will not be archived.
    """
    
    _log = logging.getLogger('archive')

    def __init__(self, name, master=None,
                 completekey='tab', stdin=None, stdout=None):
        super().__init__(name, master, completekey, stdin, stdout)
        
    def do_project(self, text):
        """Archive tasks in a given project if all tasks are closed"""
        lib = self.master.lib
        args = archive_project_parser.parse_args(text.split())
        tasks = lib.sort_tasks(filters=args.projects,
                               filterop=any,
                               showcomplete=True)
        # tasks is a list of tuples
        self._log.info('Found %d candidates to archive', len(tasks))
        
        # create a dictionary of projects, last_date
        end_dates = {}
        open_projects = set()
                
        for num, task in tasks:
            stuff = lib.parse_task(task)
            self._log.debug('Projects: %s', stuff[6])
        
            for proj in stuff[6]:
                if stuff[3] is None:
                    open_projects.add(proj)
                    continue
                if proj not in end_dates:
                    end_dates[proj] = stuff[3]
                else:
                    end_dates[proj] = max(stuff[3], 
                                          end_dates[proj])
        for proj in open_projects:
            self._log.warn('Project %s is still open. Not archived.')
            if proj in end_dates:
                del end_dates[proj]
        
        if not end_dates:
            self._log.info("No projects to archive")
            return None
    
        self._log.debug('end dates: %s', end_dates)
        
        projects_to_archive = []
        tasks_to_archive = set()
        
        now = datetime.datetime.now()
        for proj in end_dates:
            delta = now - end_dates[proj]
            if delta.days >= args.days:
                projects_to_archive.append(proj)
            else:
                self._log.warn('Project %s is not old enough to archive', proj)
        
        if not projects_to_archive:
            self._log.info("No projects to archive")
            return None
            
        for num, task in tasks:
            for proj in projects_to_archive:
                if proj in task:
                    tasks_to_archive.add(num)
                    
        tasks = lib.get_tasks(lib.config['Files']['task-path'])
        done = lib.get_tasks(lib.config['Files']['done-path'])
        
        try:
            next_done = max(done) + 1
        except ValueError:
            next_done = 1
        
        for key in tasks_to_archive:
            done[next_done] = tasks[key]
            next_done += 1
            tasks.pop(key)
        
        self._log.info("Archived %d tasks", len(tasks_to_archive))
        lib.write_tasks(tasks, lib.config['Files']['task-path'])
        lib.write_tasks(done, lib.config['Files']['done-path'])
                