# -*- coding: utf-8 -*-
"""
Created on Wed Mar  9 15:12:07 2016

@author: jenglish
"""

import basetaskerplugin


class ReportsPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Reports')
        self.setConfigOption('public_methods', 'do_projects,do_contexts')
        super().activate()
        
    def do_projects(self, text):
        """Print a list of current projects with the number of
        open and closed tasks"""
        self.project_report()
        
    def do_contexts(self, text):
        """Print a list of current contexts with the number of
        open and closed tasks"""
        self.context_report()

    def _get_project_counts(self):
        """Generate a dictionary of dictionaries showing project counts"""
        projects = {}
        tasks = self.cli.get_tasks(self.cli.config['Files']['task-path'])
        for task in list(tasks.values()):
            c, p, s, e, t, o, j, x = self.cli.parse_task(task)
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

        print("Project, open, closed")
        projects = self._get_project_counts()
        for project in sorted(projects):
            if projects[project]['open']:
                print((project, projects[project]['open'], projects[project]['closed']))

    def closed_projects(self):
        """Print a list of projects with no open tasks"""
        print("Closed Projects")
        projects = self._get_project_counts()
        for project in sorted(projects):
            if projects[project]['open'] == 0:
                print((project, projects[project]['closed']))
        if not projects:
            print("None")

    def context_report(self):
        """Print a list of contexts, noting number of open and closed tasks."""
        contexts = {"NO CONTEXT": {'open': 0, 'closed': 0}}
        tasks = self.cli.get_tasks(self.cli.config['Files']['task-path'])
        for task in list(tasks.values()):
            c, p, s, e, t, o, j, x = self.cli.parse_task(task)
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
