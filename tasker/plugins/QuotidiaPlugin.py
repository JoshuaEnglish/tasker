# -*- coding: utf-8 -*-
"""
About Quotidia
==============

Quotidia allows you to schedule tasks to appear in your task list
under certain time-given constraints. For example, a reminder to
pay rent on the first of each month, or to run a report every Monday.

Each quotidium needs the following attributes:
QID: System generated quote ID
Text to add: including the Priority, if any
Day Filter: SMTWRFY - any letter matching the days it should run
Time Filter: first time the task should be listed (hold off on this idea)
Last Addition: datetime stamp of the last time this item was added.

Basic idea: On load, this should scan the quotidia and see if today matches a
day the quotidium should be run. Then compare the last addition time to the
current time. If it has appeared in the last 24 hours ... hold on. That won't
work if I don't launch the program until the afternoon on Monday, then
everything will be delayed until the next afternoon. I just need to check if
the thing was run on the same day as today. This can be a day check.  """

import os
import argparse
import datetime
import json
import pathlib
import re
import logging

import basetaskerplugin
import minioncmd

LOG = logging.getLogger("quotidia")


QUOTIDIA = os.path.join(os.path.dirname(__file__), 'quotidia')

CLEAN_VOCABULARY = re.compile(r"^[@+]")

CLI_ABOUT = """Quotidia allows you to define tasks on a recurring basis."""


class Quotidium:
    def __init__(self, qid: str, text: str, days: str, history=None):
        self.qid = qid
        self.text = text
        self.days = days
        self.history = history if history else []

    @property
    def as_dict(self):
        this = {
            '__quotidia__': True,
            'qid': self.qid,
            'text': self.text,
            'days': self.days,
            'history': [d.isoformat() for d in self.history]}
        return this

    def __str__(self):
        return f"{self.qid}: `{self.text}` on {self.days}"

    @property
    def task_text(self):
        return f"{self.text} {{qid:{self.qid}}}"

    @property
    def last_run(self):
        return max(self.history, default=datetime.date.min)


class QuotidiaEncoder(json.JSONEncoder):
    def default(self, quotidia):
        if isinstance(quotidia, Quotidium):
            return quotidia.as_dict
        else:
            return super().default(quotidia)


def load_quotidia(dct):
    if "__quotidia__" in dct:
        return Quotidium(
            dct['qid'],
            dct['text'],
            dct['days'],
            [datetime.date.fromisoformat(d) for d in dct['history']])
    return dct


class QuotidiaLib:
    def __init__(self, directory):
        self.directory = pathlib.Path(directory)
        if not os.path.exists(directory):
            os.mkdir(directory)
        self.quotidia_path = os.path.join(directory, 'quotidia.xml')
        self.archive_path = os.path.join(directory, 'archive.xml')
        self._qids = {}
        self.now = datetime.datetime.now()
        self.daycode = "MTWRFYS"[self.now.weekday()]
        self.get_quotidia()

    @property
    def quotidia(self):
        return self._qids

    def get_quotidia(self):
        for qfile in list(self.directory.glob("*.quotidia")):
            self._qids[qfile.stem] = json.loads(qfile.read_text(),
                                                object_hook=load_quotidia)

    def add_quotidia(self, qid, text, days):
        q = Quotidium(qid, text, days)
        fname = "%s.quotidia" % qid
        json.dump(q, (self.directory / fname).open(mode='w'),
                  cls=QuotidiaEncoder)
        LOG.info('Saved %s', qid)
        self._qids[qid] = q

    def save_quotidium(self, q):
        fname = f"{q.qid}.quotidia"
        json.dump(q, (self.directory / fname).open(mode="w"),
                  cls=QuotidiaEncoder)
        LOG.info('saved %s', q.qid)

    def get_todays_quotidia(self):
        now = datetime.datetime.now()
        daycode = "MTWRFYS"[now.weekday()]
        LOG.debug("Checking for quotidia with daycode %s", daycode)
        return {(qid, q) for (qid, q) in self._qids.items()
                if daycode in q.days}

    def process_quotidia(self):
        q_to_run = []
        for (qid, q) in self.get_todays_quotidia():
            days = (self.now.date() - q.last_run).days
            if days > 0:
                q_to_run.append(q)
        return q_to_run

    def run_quotidia(self, qid):
        if qid not in self._qids:
            LOG.error('Cannot run qid %s: does not exist', qid)
            raise ValueError('Cannot run qid %s: qid does not exist' % qid)
        self._qids[qid].history.insert(0, datetime.date.today())
        LOG.debug('Updated qid %s with current time', qid)
        self.save_quotidium(self._qids[qid])


class QuotidiaCLI(minioncmd.MinionCmd):
    prompt = "quotidia> "
    minion_header = "Other subcommands (type <topic> help)"
    doc_leader = """Quotidia Help

    Create and use pre-programmed tasks to generate sequentially without
    clogging up the Z-priority list
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 quotidia_dir=None):
        super().__init__('quotidia',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)

        self.qlib = QuotidiaLib(quotidia_dir)  # should come from the plugin

    def do_run(self, text=None):
        """Process the available quotidia"""
        if text is None:
            text = "pass"
        else:
            text = text.strip().lower()
        quotidia = self.qlib.process_quotidia()
        qcount = 0
        for q in quotidia:
            if text == 'debug':
                print('Adding', q)
            self.master.cmdqueue.append(f"add {q.task_text}")
            self.qlib.run_quotidia(q.qid)
            qcount += 1

        if qcount:
            print(f"Added {qcount} tasks")
        else:
            print('No new quotidia')

    def do_list(self, text):
        """Usage: list

        List current quotidia
        """
        print("Quotidia list:", file=self.stdout)
        for idx, flow in enumerate(self.qlib.quotidia, start=1):
            print(idx, flow, file=self.stdout)
        print()

    def do_info(self, text):
        """Usage: info NAME

        Print the details of a given quotidia.
        """
        text = text.strip()
        if text not in self.qlib.quotidia:
            print('No quotidia named "{}" found'.format(text))
            return
        q = self.qlib.quotidia[text]
        print(q, "Last run on:", q.last_run)

    def do_create(self, text):
        """Usage: create NAME

        Create a new quotidia. A wizard collects the necessary information.
        """
        newname = text.strip().split()

        if len(newname) == 0:
            self._log.error("No name specified")
            print("Please provide a single-word name for the new workflow")
            return None

        if len(newname) > 1:
            self._log.error("Too many names given for workflow")
            print("Please provide a single-word name for the workflow")
            return None

        newname = newname[0]
        if newname in self.qlib.quotidia:
            self._log.error('Quotidia %s already exists', newname)
            print("Quotidia %s already existis" % newname)
            return None

        text = input("Please enter the text for this quotidia: ")
        if not text:
            print("Canceling")
            return None

        day_ok = False
        while not day_ok:
            days = input("Please enter the days to run: [SMTWRFY]")
            day_ok = re.match(r"^S?M?T?W?R?F?Y?$", days)

        fname = "%s.quotidia" % newname
        self.qlib.add_quotidia(newname, text, days)
        print("Created new quotidia in", fname)

    def help_about(self):
        """About this plugin"""
        print(CLI_ABOUT)


class Quotidia(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        LOG.debug("Activaing Quotidia")
        self._log.debug("Activating Quotidia")
        if not self.hasConfigOption('directory'):
            self._log.debug("Setting Directory to default")
            self.setConfigOption('directory', QUOTIDIA)

        if not self.hasConfigOption('hidden-extensions'):
            self.setConfigOption('hidden-extensions', 'qid')

        quotidia_folder = self.getConfigOption('directory')

        self.cli_name = 'quotidia'
        self.cli = QuotidiaCLI(
            quotidia_dir=quotidia_folder)  # needs to be an instance

        parser = self.parser = argparse.ArgumentParser('quotidia')
        self.helpstr = 'Quotidia commands (see `help quotidia`)'
        quotidia_commands = parser.add_subparsers(title='quotidia commands',
                                                  dest='subcommand',
                                                  metavar='')

        quotidia_commands.add_parser('list', help='lists known quotidia')
        run = quotidia_commands.add_parser('run', help='manually run quotidia')
        run.add_argument('text', help="optional subcommand (debug)",
                         default="pass", nargs='?')
        info = quotidia_commands.add_parser('info',
                                            help='details on a quotidium')
        info.add_argument('name', help="the name of the quotidium")

        create = quotidia_commands.add_parser('new',
                                              help='create a new quotidium')
        create.add_argument('name',
                            help='the name of the new quotidium')

        super().activate()
