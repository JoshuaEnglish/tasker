
"""
ClipboardPlugin

Adds the clip command to the cli.

Created on 2017-01-25T16:26:34.706840

@author: Josh English
"""
import re
import argparse
import basetaskerplugin

import pyperclip


class ClipboardPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Clipboard')
        # edit the following line
        if not self.hasConfigOption('public_methods'):
            self.setConfigOption('public_methods', 'do_clip')

        # define argument parsers
        self.clip_parser = clipboard = argparse.ArgumentParser('clip')
        clipboard.add_argument('n', type=int,
                               help="number of the task to copy "
                                    "to the clipboard")
        clipboard.add_argument('regex', nargs=argparse.ZERO_OR_MORE,
                               help='Optional Regular Expression',
                               default=[".*"])

        # add parsers

        self.parsers = {
            clipboard: "Allows copying to system clipboard",
        }

        super().activate()

    def do_clip(self, text):
        """copies a task to the clipboard by number"""
        args = self.clip_parser.parse_args(text.split())
        tasks = self.lib.get_tasks(self.lib.config['Files']['task-path'])
        if args.n not in tasks:
            print("Task number %s not in tasks" % args.n)
            return False
        else:
            regex = " ".join(args.regex)
            m = re.search(regex, tasks[args.n].text)
            if m:
                pyperclip.copy(m.group())
                print("Copied to clipboard:", m.group())
                return True
            else:
                print("Nothing found. Nothing copied")
                return False

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
        this.text = this.text.replace('{p}', pyperclip.paste())

        return (0, "", this)

    def help_clipping(self):
        """Clipping allows you to use {p} in a task and have it be replaced
        with the contents of the clipboard."""

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
        this.text = this.text.replace('{p}', pyperclip.paste())

        return (0, "", this)
