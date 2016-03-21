# -*- coding: utf-8 -*-
"""
Created on Wed Mar 16 14:04:54 2016

@author: jenglish
"""
import sys
import os
import argparse
import logging

from configparser import ConfigParser
import yapsy.ConfigurablePluginManager as CPM

import basetaskerplugin
import minioncmd
import core
import lib

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m%d %H:%M:%S')

log = logging.getLogger('main')

config = ConfigParser()
config.read_dict(
    {'Files': {'tasker-dir': os.path.join(os.environ['APPDATA'], 'tasker'),
               'task-path': "%(tasker-dir)s/todo.txt",
               'done-path': "%(tasker-dir)s/done.txt",
               },
     'Tasker': {'hidden_extensions': 'uid'}})

if hasattr(sys, "frozen"):
    configdir = os.path.dirname(sys.executable)
else:
    configdir = os.path.dirname(__file__)

configpath = os.path.join(configdir, 'tasker.ini')

config.read(configpath)


def save_config():
    with open(configpath, 'w') as fp:
        config.write(fp)


parser = argparse.ArgumentParser('t', description="Todo Manager")
commands = parser.add_subparsers(title='commands',
                                 dest="command",
                                 help="supported commands",
                                 )
parser.add_argument('-i', '--interactive', '-l', '--loop', dest="interact",
                    action='store_true', default=False,
                    help='enter the interactive loop')

feedback = parser.add_mutually_exclusive_group()
feedback.add_argument('-d', '--debug', action='store_const', const=2,
                      dest='verbose', default=0,
                      help="show all debug messages")
feedback.add_argument('-v', '--verbose', action='count', default=0,
                      help="show more process details (can repeat)")
feedback.add_argument('-q', '--quiet', action='count', default=0,
                      help="show fewer process details (can repeat)")
core.add_core_subparsers(commands)


def add_subparser(subparser, helpstr=None):
    """add_subparser(subparser [,helpstr])
    Adds an argparse.ArgumentParser instance to the main parser.
    """

    if not isinstance(subparser, argparse.ArgumentParser):
        raise TypeError("Subparser must be an instance of ArgumentParser")

    helpstr = helpstr or "Dunno. Ask the plugin creator."

    name = subparser.prog  # assume no prefix commands have been put in

    subparser.prog = "%s %s" % (parser.prog, name)
    commands.choices[name] = subparser

    # to include this in help we need include the help string
    choice_action = commands._ChoicesPseudoAction(name, (), helpstr)
    commands._choices_actions.append(choice_action)


# assume report_parser is defined elsewhere and imported
report_parser = argparse.ArgumentParser('report')
report_parser.add_argument('text', nargs=argparse.REMAINDER)


class TaskCmd(minioncmd.BossCmd):
    prompt = "tasker> "
    doc_leader = "Tasker Help"

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 config=None, lib=None):
        super().__init__(completekey, stdin, stdout)

        self.config = config
        self.lib = lib

    def do_list(self, line):
        "Lists tasks"
        args = commands.choices['list'].parse_args(line.split())
        print(self.lib.list_tasks(**vars(args)))

    def do_add(self, line):
        """Add a task"""
        args = commands.choices['add'].parse_args(line.split())
        print(self.lib.add_task(" ".join(args.text)))

    def do_do(self, line):
        """Mark a task as complete"""
        args = commands.choices['do'].parse_args(line.split())
        print(self.lib.complete_task(args.tasknum, " ".join(args.comment)))

    def do_pri(self, line):
        """Prioritize a task: NUM, PRI, (NOTE)"""
        args = commands.choices['pri'].parse_args(line.split())
        print(self.lib.prioritize_task(**vars(args)))


manager = CPM.ConfigurablePluginManager(config,
                                        config_change_trigger=save_config)
manager.setPluginPlaces(['plugins'])
manager.setCategoriesFilter({
    "NewCommand": basetaskerplugin.NewCommandPlugin,
    "SubCommand": basetaskerplugin.SubCommandPlugin,
    "Generic": basetaskerplugin.TaskerPlugin,
})

LIB = lib.TaskLib(config, manager)
CLI = TaskCmd(config=config, lib=LIB)

core.PluginCmd('plugins', CLI, manager)
add_subparser(core.plugin_argparser, "Plugin manager")

log.debug('Collecting Plugins...')
manager.collectPlugins()

for info in manager.getAllPlugins():
    if not info.is_activated:
        continue
    plugin = info.plugin_object
    plugin.lib = LIB
    
    plugin.CONFIG_SECTION_NAME = "%s Plugin: %s" % (info.category, info.name)
    if hasattr(plugin, 'parser'):
        log.debug("Adding command line parser for %s", info.name)
        add_subparser(plugin.parser, getattr(plugin, 'helpstr', None))
    elif hasattr(plugin, 'parsers'):
        for newparser in plugin.parsers:
            log.debug('Adding command parser for %s', newparser.prog)
            add_subparser(newparser, plugin.parsers[newparser])

def load_plugins():
    # process activated plugins

    for info in manager.getAllPlugins():
        if not info.is_activated:
            continue
        plugin = info.plugin_object

        if info.category == 'SubCommand':
            if hasattr(plugin, 'cli'):
                name = getattr(plugin, 'cli_name')
                cli = getattr(plugin, 'cli')
                CLI.add_minion(name, cli)
            else:
                log.warn("Subcommand plugin %s has no MinionCmd instance", info.name)
        elif info.category == 'NewCommand':
            methods = plugin.getConfigOption('public_methods').split(',')
            methods = [m.strip() for m in methods]
            log.debug("Adding new commands: %s" % ", ".join(methods))
            for method in methods:
                setattr(CLI.__class__, method, getattr(plugin, method))



def main():
    import sys
    args = parser.parse_args(sys.argv[1:])
    print(args)
    logging.root.setLevel(30 - (args.verbose - args.quiet) * 10)
    load_plugins()

    if args.interact:
        CLI.cmdloop()
    elif not args.command:
        CLI.onecmd('list')
    else:
        CLI.onecmd(' '.join(sys.argv[1:]))




if __name__ == '__main__':
    main()