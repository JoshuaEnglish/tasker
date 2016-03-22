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

class ReportsPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Reports')
        self.setConfigOption('public_methods', 'do_projects,do_contexts')

        # this is a case where we need to add multiple commands to the main
        # argument parser
        project = argparse.ArgumentParser('projects')
        project.add_argument('--closed', action='store_true',
                             help="list closed projects")

        context = argparse.ArgumentParser('contexts')
        context.add_argument('text', nargs=argparse.REMAINDER)

        self.parsers = {
            project: "Project reports",
            context: "Context reports"
        }

        super().activate()

    def do_projects(self, text):
        """Print a list of current projects with the number of
        open and closed tasks"""
        if text == 'closed':
            self.closed_projects()
        else:
            self.project_report()

    def do_contexts(self, text):
        """Print a list of current contexts with the number of
        open and closed tasks"""
        self.context_report()

    def _get_project_counts(self):
        """Generate a dictionary of dictionaries showing project counts"""
        projects = {'NO PROJECT': {'open': 0, 'closed': 0}}
        tasks = self.lib.get_tasks(self.lib.config['Files']['task-path'])
        for task in list(tasks.values()):
            c, p, s, e, t, o, j, x = self.lib.parse_task(task)
            if not j:
                if c:
                    projects['NO PROJECT']['closed'] += 1
                else:
                    projects['NO PROJECT']['open'] += 1
            for project in j:
                if project not in projects:
                    projects[project] = {'open': 0, 'closed': 0}
                if c:
                    projects[project]['closed'] += 1
                else:
                    projects[project]['open'] += 1
        return projects

    def project_report(self):
        """Print a list of project, noting number of open and closed tasks."""

      
        projects = self._get_project_counts()
        
        lister.print_list([(proj, 
                            str(projects[proj]['open']), 
                            str(projects[proj]['closed']))
                           for proj in projects
                           if projects[proj]['open']],
                          "Project Open Closed".split())

    def closed_projects(self):
        """Print a list of projects with no open tasks"""
        print("Closed Projects")
        projects = self._get_project_counts()
        for project in sorted(projects):
            if projects[project]['open'] == 0:
                print(project, projects[project]['closed'])
        if not projects:
            print("None")

    def context_report(self):
        """Print a list of contexts, noting number of open and closed tasks."""
        contexts = {"NO CONTEXT": {'open': 0, 'closed': 0}}
        tasks = self.lib.get_tasks(self.lib.config['Files']['task-path'])
        for task in list(tasks.values()):
            c, p, s, e, t, o, j, x = self.lib.parse_task(task)
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
                print(context, contexts[context]['open'],
                      contexts[context]['closed'])
