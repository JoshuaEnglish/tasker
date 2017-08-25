# -*- coding: utf-8 -*-
"""
ReporterPlugin

Provide Tasker with three new commands: project, contexts, and today

Created on Wed Mar  9 15:12:07 2016

@author: jenglish
"""
import os
import datetime

import argparse
import basetaskerplugin
import lister
import textwrap

from lib import re_ext

todo = """
Create a timed report
"""

__version__ = '1.2'
__updated__ = '2017-01-26'
__history__ = """
1.1 -- today report to the screen is wrapped
1.2 -- today report allows optional numbers of days ago
"""


class ReportsPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Reports')
        self.setConfigOption('public_methods',
                             'do_projects,do_contexts,do_today')
        self.setConfigOption('daily_report_filename',
                             "{0.year}-{0.month}-{0.day}")

        # this is a case where we need to add multiple commands to the main
        # argument parser

        common_opts = argparse.ArgumentParser(add_help=False)
        group = common_opts.add_mutually_exclusive_group()

        group.add_argument('--closed', action='store_true',
                           default=False, dest='include_closed',
                           help="include results with no open tasks")

        group.add_argument('--archive', action='store_true',
                           default=False, dest='include_archive',
                           help='Include the archive in the report')

        group.add_argument('--only', action='store_true',
                           default=False, dest='only_archive',
                           help='Only look in the archive')

        group.add_argument('--nowait', action='store_true',
                           default=False, dest='only_active',
                           help="Only list projects without a (Z) priority")

        project = argparse.ArgumentParser(
            'projects', parents=[common_opts],
            description="""Print a list of current projects with the number of
        open and closed tasks.
        """
        )
        self.project_parser = project

        context = argparse.ArgumentParser(
            'contexts', parents=[common_opts],
            description="""Print a list of current contexts with the number """
                        """of open and closed tasks""")
        self.context_parser = context

        today = argparse.ArgumentParser(
            'today', description="""Print a list of tasks completed on """
                                 """the current day (or n days ago)""")

        today.add_argument('-f', dest='tofile', default=False,
                           action='store_true',
                           help="Write output to a daily file")
        today.add_argument('-c', dest='bycomplete', default=False,
                           action='store_true',
                           help="Sort by completed time")
        today.add_argument('-t', dest='trimoutput', default=False,
                           action='store_true',
                           help="Trim output to dates only")
        today.add_argument('days', default=0, type=int, nargs='?',
                           help="Days ago to process")
        self.today_parser = today

        # the main program will gather these parsers after activation
        self.parsers = {
            project: "Project reports",
            context: "Context reports",
            today: "Daily report"
        }

        super().activate()

    def help_projects(self):
        self.project_parser.print_help()

    def do_projects(self, text):
        """Print a list of current projects with the number of
        open and closed tasks.
        """

        args = self.project_parser.parse_args(text.split())
        args.name = 'project'
        self.print_counts(**vars(args))

    def help_contexts(self):
        self.context_parser.print_help()

    def do_contexts(self, text):
        """Print a list of current contexts with the number of
        open and closed tasks"""
        args = self.context_parser.parse_args(text.split())
        args.name = 'context'
        self.print_counts(**vars(args))

    def help_today(self):
        self.today_parser.print_help()

    def do_today(self, text):
        """Print a list of tasks completed on the current day"""
        args = self.today_parser.parse_args(text.split())
        today = datetime.datetime.today().date()
        today -= datetime.timedelta(days=args.days)
        print("Processing report for", today)

        tasks = self.lib.sort_tasks(by_pri=False, filters=None,
                                    filterop=None, showcomplete=True)

        closed_tasks = [t for k, t in tasks if t.complete]
        today_tasks = [t for t in closed_tasks if t.end.date() == today]

        if args.bycomplete:
            today_tasks.sort(key=lambda t: t.end)

        indent = 40
        if args.trimoutput:
            trimmed_tasks = []
            indent = 22
            for t in today_tasks:
                s = "{0.start:%Y-%m-%d} {0.end:%Y-%m-%d} {0.text}".format(t)
                s = re_ext.sub("", s)
                trimmed_tasks.append(s)
            today_tasks = trimmed_tasks
        else:
            today_tasks = [str(t)[2:] for t in today_tasks]
        # wrap_width = self.config['Tasker'].getint('wrap-width', 78)
        textwrapper = textwrap.TextWrapper(width=78,
                                           subsequent_indent=' ' * indent)

        for task in today_tasks:
            print(textwrapper.fill(task))

        if args.tofile:
            folder = self.getConfigOption('daily_report_directory')
            if not os.path.exists(folder):
                os.mkdir(folder)
            filename = self.getConfigOption('daily_report_filename').format(
                today)
            with open(os.path.join(folder, filename), 'w') as fp:
                for task in today_tasks:
                    fp.write("%s\n" % (task))

    def print_counts(self, name, include_closed=False, include_archive=False,
                     only_archive=False, only_active=False):
        """Print a list of report, noting number of open and closed tasks.

        :param str name:
        :param bool include_closed: Include closed tasks
        :param bool include_archive: Include archived tasks
        :param bool only_archive: Only show archived tasks
        :param bool only_active: Don't include projects that are priority Z
        """

        show_closed = any((include_closed, include_archive, only_archive))
        counts = self.lib.get_counts(name.lower(),
                                     include_archive,
                                     only_archive)
        self._log.debug(counts)
        show_list = any((k['open'] for k in counts.values()))

        def s(k):
            """Tuplize a count"""
            return (self.lib.get_color('open') + str(k),
                    str(counts[k]['open']),
                    str(counts[k]['closed'])
                    )

        def f(k):
            """Determine if a count should be in the list"""
            yahsure = counts[k]['open'] or show_closed
            if only_active:
                yahsure = yahsure and (counts[k]['Z'] != counts[k]['open'])
            return yahsure

        if show_list or show_closed:
            headers = "{} Open Closed".format(name.title()).split()
            lister.print_list([s(count) for count in sorted(counts)
                               if f(count)],
                              headers)
        else:
            print("No open {}s.".format(name))
