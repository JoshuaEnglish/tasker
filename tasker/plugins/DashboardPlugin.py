"""
DashboardPlugin

Manages a dashboard for projects, allowing for updates to projects that aren't
task-oriented (like getting updates from other people, experimenting, etc.)

Created on 2017-09-19T10:10:16

@author: Josh English
"""
import os
import argparse
import datetime
import textwrap
import xml.etree.ElementTree as ET

import basetaskerplugin
import minioncmd
import lister

DASHBOARD = os.path.join(os.path.dirname(__file__), 'dashboards')


class DashboardError(ValueError):
    pass


NEW = 'NEW'
WORKING = 'WORKING'
DONE = 'DONE'
ZOMBIED = 'ZOMBIED'

NOW = 'NOW'
LATER = 'LATER'
PENDING = 'PENDING'


class DashboardLib(object):
    def __init__(self, directory):
        self.directory = directory
        if not os.path.exists(directory):
            os.mkdir(directory)
        self.dashboard_path = os.path.join(directory, 'dashboard.xml')
        self.archive_path = os.path.join(directory, 'archive.xml')
        self.dashboard = self.get_dashboard()
        self.display_format = "%x %I:%M:%S %p"
        self.time_format = "%Y-%m-%dT%H:%M:%S"

    def get_dashboard(self):
        """Get the dashboard node, creating a stub file if needed"""
        if os.path.exists(self.dashboard_path):
            return ET.parse(self.dashboard_path).getroot()
        else:
            return ET.Element('dashboard')

    def write_dashboard(self):
        """Write the dashboard node to a file"""
        with open(self.dashboard_path, 'w') as f:
            f.write(ET.tostring(self.dashboard).decode())

    def get_archive(self):
        """Get the archive node, creating a stub file if needed"""
        if os.path.exists(self.archive_path):
            return ET.parse(self.archive_path).getroot()
        else:
            return ET.Element('achive')

    def write_archive(self):
        """Write the archive node to a file"""
        with open(self.archive_path, 'w') as f:
            f.write(ET.tostring(self.archive).decode())

    def list_projects(self):
        """Return list of project names in the dashboard file"""
        return [proj.get('id') for proj in self.dashboard.findall('project')]

    def new_project(self, projectid, name, background,
                    status=NEW, priority=NOW):
        """new_project(projectid, name background)
        Create a new project
        """
        if projectid in self.list_projects():
            raise DashboardError("Duplicated Project ID %s", projectid)
        now = datetime.datetime.now()
        node = ET.Element('project')
        node.set('id', projectid)
        node.set('created', now.strftime(self.time_format))
        node.set('modified', now.strftime(self.time_format))
        node.set('status', status)
        node.set('priority', priority)
        node.tail = '\n'
        _name = ET.SubElement(node, 'name')
        _name.text = name.strip()
        bg = ET.SubElement(node, 'background')
        bg.text = background.strip()
        self.dashboard.append(node)
        self.write_dashboard()

    def add_project_note(self, projectid, stub, text):
        """add_project_note(projectid, stub, text)
        Add a note to a project.

        stub is a small text description
        text is a longer text description
        """
        node = self.dashboard.find('project[@id="%s"]' % projectid)
        if node is None:
            raise DashboardError("Project id %s not in dashboard" % projectid)
        now = datetime.datetime.now()
        node.set('modified', now.strftime(self.time_format))
        if node.get('status') == NEW:
            node.set('status', WORKING)
        elif node.get('status') == DONE:
            node.set('status', ZOMBIED)

        note = ET.SubElement(node, 'note')
        note.set('created', now.strftime(self.time_format))
        ET.SubElement(note, 'stub').text = stub.strip()
        ET.SubElement(note, 'text').text = text.strip()
        self.write_dashboard()
        return True

    def complete_project(self, projectid, text):
        """complete_project(projectid, text)
        Add a note to the project that the project is closed. Set status to
        DONE.
        """
        node = self.dashboard.find('project[@id="%s"]' % projectid)
        if node is None:
            raise DashboardError("Project id %s not in dashboard" % projectid)
        if node.get('status') == DONE:
            return False
        now = datetime.datetime.now()
        node.set('modified', now.strftime(self.time_format))
        node.set('status', DONE)
        note = ET.SubElement(node, 'note')
        note.set('created', now.strftime(self.time_format))
        ET.SubElement(note, 'stub').text = 'Closed Project'
        ET.SubElement(note, 'text').text = text.strip()
        note.tail = '\n'
        self.write_dashboard()
        return True

    def display_time(self, timestamp):
        """Convert a timestamp to the prefered display format"""
        parsed = datetime.datetime.strptime(timestamp, self.time_format)
        return parsed.strftime(self.display_format)

    def get_dashboard_report(self):
        """Return (id, status, latest_timestamp, stub) tuples of
        dashboard items
        """
        stuff = []
        for project in self.dashboard.findall('project'):
            if project.get('status') == DONE:
                continue
            notes = sorted(project.findall('note'),
                           key=lambda x: x.get('created'))
            if notes:
                stuff.append((project.get('id'),
                              project.get('status'),
                              self.display_time(notes[-1].get('created')),
                              notes[-1].findtext('stub')))
            else:
                stuff.append((project.get('id'),
                              project.get('status'),
                              project.get('modified'),
                              project.findtext('background')[:32]))
        return stuff

    def get_project_details(self, projectid, inorder=False):
        """get_project_details(projectid [, inorder=False])
        Return a dictionary containing the text of the project.
        Keys are:
            name
            background
            created
            modified
            status
            priority
            notes - a list of (time, stub, text) tuples

        Notes are sorted in chronological order if *inorder* is true, otherwise
        in reverse chronological order (the default).
        """
        node = self.dashboard.find('project[@id="%s"]' % projectid)
        if node is None:
            raise DashboardError("Project id %s not in dashboard" % projectid)
        res = {'name': node.findtext('name'),
               'background': node.findtext('background'),
               'status': node.get('status'),
               'priority': node.get('priority'),
               'created': self.display_time(node.get('created')),
               'modified': self.display_time(node.get('modified')),
               'notes': [(self.display_time(x.get('created')),
                          x.findtext('stub'),
                          x.findtext('text')) for x in sorted(
                              node.findall('note'),
                              key=lambda x:x.get('created'),
                              reverse=not inorder)]}
        return res

    def update_priority(self, projectid, priority):
        """update_priority(projectid, priority)
        Update the projectid with the new priority. New priority must be
        "NOW", "LATER", "PENDING".
        """
        node = self.dashboard.find('project[@id="%s"]' % projectid)
        if node is None:
            raise DashboardError("Project id %s not in dashboard" % projectid)
        if priority.upper() not in [NOW, LATER, PENDING]:
            raise DashboardError("Invalid Priority %s" % priority)
        node.set('priority', priority.upper())
        self.write_dashboard()

    def update_status(self, projectid, status):
        """update_status(projectid, status)
        Update the projectid with the new status. New status must be
        "NEW", "WORKING", "DONE", "ZOMBIED"
        """
        node = self.dashboard.find('project[@id="%s"]' % projectid)
        if node is None:
            raise DashboardError("Project id %s not in dashboard" % projectid)
        if status.upper() not in [NEW, WORKING, DONE, ZOMBIED]:
            raise DashboardError("Invalid Status %s" % status)
        node.set('status', status.upper())
        self.write_dashboard()


class DashboardCLI(minioncmd.MinionCmd):
    prompt = "dashboard>"
    minion_header = "Other subcommands (type <topic> help)"
    doc_leader = """Dashboard Help

    Store notes about projects that don't tie into actionable items.
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 dashlib=None):
        super().__init__('dashboard',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.dashlib = dashlib

    def do_report(self, text):
        """Usage: report

        Print a dashboard report
        """
        headers = "ID Status Date Note".split()
        lister.print_list(self.dashlib.get_dashboard_report(), headers)

    def do_new(self, text):
        """Usage: new ID NAME+

        Create a new dashboard project. You will be prompted for required
        background information.
        """

        words = text.split()
        projectid = words.pop(0)
        name = ' '.join(words)

        background = []
        print("Please provide some background. Enter DONE on a single line to "
              "finish.")
        while True:
            text = input(">")
            if text == 'DONE':
                break
            background.append(text)

        if not background:
            print("No project created.")
            return None
        background = '\n'.join(background)
        try:
            self.dashlib.new_project(projectid, name, background)
            print("New project added")
        except DashboardError as E:
            print("ERROR:", E)

    def do_details(self, text):
        """Usage: details PROJECTID [inorder]

        Print details of a project. If second word is 'inorder' then notes
        will be printed in chronological order.
        """
        words = text.split()
        projectid = words.pop(0)
        inorder = words and words[0].lower() in ['inorder', 'true', '--inorder']
        try:
            details = self.dashlib.get_project_details(projectid, inorder)
        except DashboardError as E:
            print(E)
            return None
        print("{0:<44s}{1:>8s}{2:>8s}".format(details['name'][:44],
                                              details['status'],
                                              details['priority']))
        print('-'*60)
        print("{1:<30s}{0:>30s}\n".format("Created %s" % details['created'],
                                          "Modified %s" % details['modified']))
        print(textwrap.fill("Background: {}".format(details['background']),
                            width=60), end="\n\n")
        if details['notes']:
            print("Notes:")
            for time, stub, text in details['notes']:
                print(time, stub)
                print(textwrap.fill(text, width=60))
        else:
            print("No Notes")

    def do_status(self, text):
        """Usage: status ID [NEW, WORKING, DONE, ZOMBIED]

        Update the status of a project.
        """
        try:
            projectid, status = text.split()
        except ValueError as E:
            print(E)
            return None
        try:
            self.dashlib.update_status(projectid, status)
            print('Status Updated')
        except DashboardError as E:
            print(E)
            return None

    def do_priority(self, text):
        """Usage: priority ID [NOW, LATER, PENDING]

        Update the priority of a project.
        """
        try:
            projectid, status = text.split()
        except ValueError as E:
            print(E)
            return None
        try:
            self.dashlib.update_priority(projectid, status)
            print('Priority Updated')
        except DashboardError as E:
            print(E)
            return None

    def do_note(self, text):
        """Usage: note ID SLUG+

        Create a new dashboard note. You will be prompted for required
        background information.
        """

        words = text.split()
        projectid = words.pop(0)
        name = ' '.join(words)
        while not name:
            name = input("Please enter a slug for the note")

        background = []
        print("Please provide some background. Enter DONE on a single line to "
              "finish.")
        while True:
            text = input(">")
            if text == 'DONE':
                break
            background.append(text)

        background = '\n'.join(background)
        try:
            self.dashlib.add_project_note(projectid, name, background)
            print("New project note")
        except DashboardError as E:
            print("ERROR:", E)


class DashboardPlugin(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug('Activating Dashboard')
        if not self.hasConfigOption('directory'):
            self._log.debug('Setting Dashboard Directory to default')
            self.setConfigOption('directory', DASHBOARD)
        if not self.hasConfigOption('display-format'):
            self._log.debug('Setting Dashboard display-format to default')
            self.setConfigOption('display-format', "%x %I:%M:%S %p")

        self.cli_name = 'dashboard'
        self.dashlib = DashboardLib(self.getConfigOption('directory'))
        self.dashlib.display_format = self.getConfigOption('display-format')

        self.cli = DashboardCLI(dashlib=self.dashlib)
        #   dashboard_dir=self.getConfigOption('directory'))

        # define argument parsers
        parser = self.parser = argparse.ArgumentParser('dashboard')
        dashboard_command = parser.add_subparsers(title="Dashboard commands",
                                                  dest='subcommand',
                                                  metavar='')
        dashboard_command.add_parser(
            'report',
            help='Get current dashboard report')

        new = dashboard_command.add_parser(
            'new',
            help='Create a new project for the dashboard')
        new.add_argument('projectid',
                         help="A single keyword for this project")
        new.add_argument('name', nargs=argparse.REMAINDER,
                         help="The name of the project")

        details = dashboard_command.add_parser(
            'details',
            help='Get the details of a project')
        details.add_argument('projectid',
                             help='The id for the project')
        details.add_argument('--inorder', action='store_true', default=False,
                             help='List notes in chronological order')

        note = dashboard_command.add_parser(
            'note',
            help='Add a note to a project')
        note.add_argument('projectid',
                          help="A single keyword identifying a project")
        note.add_argument('slug', nargs=argparse.REMAINDER,
                          help="A brief description of the note")

        status = dashboard_command.add_parser(
            'status',
            help='Update the status of a project')
        status.add_argument('projectid',
                            help='A single keyword identifying a project')
        status.add_argument('status', choices=[NEW, DONE, WORKING, ZOMBIED],
                            help='The new status')

        priority = dashboard_command.add_parser(
            'priority',
            help="Update the priority of a project")
        priority.add_argument('projectid',
                              help='A single keyword identifying a project')
        priority.add_argument('priority', choices=[NOW, LATER, PENDING],
                              help='The new priority')

        # add parsers
        self.parsers = {
            parser: "Thumb twiddlers",
        }

        super().activate()

    # hook method - delete if not going to use
    def add_task(self, this):
        """Hook method called when adding tasks

        This method can access the the TaskLib instance through the
        ``self.lib`` property.

        Args:
            this: the :class:`Task` being added

        Returns:
            tuple: (code, message, this)

            code is 0 for TASK_OK or 2 for TASK_EXT_ERROR
            message is a string explaining the error (empty string if code
            is 0)
            this is the task, either as passed or if edited
        """
        return (0, "", this)

    # hook method - delete if not going to use
    def complete_task(self, this):
        """Hook method called when completing tasks

        This method can access the the TaskLib instance through the
        ``self.lib`` property.

        Args:
            this: the :class:`Task` being added

        Returns:
            tuple: (code, message, this)

            code is 0 for TASK_OK or 2 for TASK_EXT_ERROR
            message is a string explaining the error (empty string if code
            is 0)
            this is the task, either as passed or if edited
        """

        return (0, "", this)
