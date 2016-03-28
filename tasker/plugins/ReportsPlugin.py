# -*- coding: utf-8 -*-
"""
ReporterPlugin

Provide Tasker with two commands: project and contexts

Created on Wed Mar  9 15:12:07 2016

@author: jenglish
"""
import argparse
import basetaskerplugin
import lister

todo = """
Create a timed report
"""
class ReportsPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Reports')
        self.setConfigOption('public_methods', 'do_projects,do_contexts')

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
        
        project = argparse.ArgumentParser('projects', parents=[common_opts])
        self.project_parser = project

        context = argparse.ArgumentParser('contexts', parents=[common_opts])
        self.context_parser = project
        
        # the main program will gather these parsers after activation
        self.parsers = {
            project: "Project reports",
            context: "Context reports"
        }

        super().activate()

    def do_projects(self, text):
        """Print a list of current projects with the number of
        open and closed tasks"""
        args = self.project_parser.parse_args(text.split())
        args.name='project'
        self.print_counts(**vars(args))
        #self.project_report(**vars(args))

    def do_contexts(self, text):
        """Print a list of current contexts with the number of
        open and closed tasks"""
        args = self.context_parser.parse_args(text.split())
        args.name='context'
        self.print_counts(**vars(args))
        

    def print_counts(self, name, include_closed=False, include_archive=False, 
                     only_archive=False):
        """Print a list of report, noting number of open and closed tasks.

        :param bool include_closed: Include closed tasks
        :param bool include_archive: Include archived tasks
        :param bool only_archive: Only show archived tasks
        """

        show_closed = any((include_closed, include_archive, only_archive))
        counts = self.lib.get_counts(name.lower(), 
                                     include_archive, 
                                     only_archive)
        show_list = any((k['open'] for k in counts.values()))
        if show_list or show_closed:
            headers = "{} Open Closed".format(name.title()).split()
            s = lambda k: (str(k), 
                           str(counts[k]['open']), 
                           str(counts[k]['closed']))
            lister.print_list([s(count) for count in sorted(counts)
                               if (counts[count]['open'] or show_closed)],
                              headers)
        else:
            print("No open {}s.".format(name))


