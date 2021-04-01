
"""
TimetrackerPlugin

Twiddles its thumbs

Created on 2019-01-16T11:35:10.403023

@author: englisjo
"""
import logging
import datetime
import argparse
import pathlib
import basetaskerplugin
import minioncmd

HERE = pathlib.Path(__file__).resolve().parent
TRACKER = HERE / 'tracker'


class TimeTrackerLib(object):
    def __init__(self, directory):
        self._log = logging.getLogger('timetrackerlib')
        self._log.info('creating TimetrackeLib')
        self.directory=pathlib.Path(directory)
        if not self.directory.exists():
            self.directory.mkdir()
        self.tracker_path = self.directory / 'tracker.txt'



class TimetrackerCLI(minioncmd.MinionCmd):
    prompt = "track>"
    minion_header = 'Other subcommands (type <subcommand> help)'
    doc_leader = """Time Tracker Help

    Logs start and stop time for open tasks
    """

    def __init__(self, completekey='tab', stdin=None, stdout=None,
                 checklib=None):
        super().__init__('checklist',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)
        self.checklib = checklib

    def do_start(self, text):
        '''Usage: start region +words

        Start tracking an action. The region could be a specific application
        or project
        '''
        pass


class TimetrackerPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Timetracker')
        # edit the following line
        self.setConfigOption('public_methods', 'do_track')
        self.setConfigOption('tracker_folder', 'here')

        # define argument parsers
        timetracker = argparse.ArgumentParser('track')

        # add parsers

        self.parsers = {
            timetracker: "Simple activity logger",
        }

        super().activate()

    def do_track(self, text):
        """Thumb twiddler"""
        pass

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
