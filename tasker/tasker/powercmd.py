# -*- coding: utf-8 -*-

"""PowerCmd

Undocumented Power User features.
This allows for more powerful under the hood commands in the prompt that
would not be available normally.

It is a minioncmd with no argument parser.

Access by typing tasker.py --power. This will begin the interactive prompt.
"""
import os
import logging

import minioncmd


# noinspection PyIncorrectDocstring
class PowerCmd(minioncmd.MinionCmd):
    """PluginCmd(name [,master, manager, completekey, stdin, stout])
    Poweruser interactive prompt commands.
    """

    prompt = "power> "
    doc_leader = "Power User Help"
    _log = logging.getLogger('poweruser')

    def do_qlist(self, line):
        """lists all items in the command queue."""
        if not self.master.cmdqueue:
            self.stdout.write("No Queued Commands\n")
        for item in self.master.cmdqueue:
            self.stdout.write("Queued Command: {}\n".format(item))

    # noinspection PyIncorrectDocstring
    def do_sections(self, line):
        """Lists the configuration sections"""
        config = self.master.config
        for section in config.sections():
            print(section)

    def do_items(self, line):
        """lists items in a given section"""
        config = self.config
        if not line.strip() in config.sections():
            print("Section not found")
            return None
        for key, val in config.items(line.strip(), True):
            print(key, "=", val)

    def do_set(self, line):
        """Sets SECTION OPTION VALUE"""
        config = self.config
        try:
            section, option, value = line.split(maxsplit=2)
            config.set(section, option, value)
            if self.master:
                self._log.info("Setting option. Saving configuration file")
                self.master.save_config()
            else:
                self._log.info("No master command. Cannot save options.")

        except Exception as E:
            print(E)
            
    def do_openfolder(self, line):
        """Opens the tasker file directory"""
        os.startfile(self.config['Files']['tasker-dir'])
