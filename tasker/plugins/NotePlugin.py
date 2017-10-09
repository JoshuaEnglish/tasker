"""
AttachPlugin

Store text notes that can be attached to items or projects.

These will have to be called attachements as 'note' has meaning already

Created on 2017-07-21T10:44:17.239708

@author: Josh English
"""
import argparse
import basetaskerplugin


import minioncmd

class AttachCLI(minioncmd.MinionCmd):
    prompt = "attach> "

    def __init__(self, completekey='tab', stdin=None, stdout=None, ):
        super().__init__('attach',
                         completekey=completekey,
                         stdin=stdin,
                         stdout=stdout)


class AttachPlugin(basetaskerplugin.SubCommandPlugin):
    def activate(self):
        self._log.debug('Activating Attachments')
        # edit the following line
        self.setConfigOption('public_methods', 'do_attach')


        self.cli_name = 'attach'
        self.cli = AttachCLI()


        # define argument parsers
        note = argparse.ArgumentParser('note')

        # add parsers

        self.parsers = {
            note: "Attachment manager",
        }

        super().activate()

    def do_attach(self, text):
        """Create an attachment"""
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


