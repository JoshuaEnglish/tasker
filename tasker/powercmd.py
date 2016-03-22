# -*- coding: utf-8 -*-

"""PowerCmd

Undocumented Power User features.
This allows for more powerful under the hood commands in the prompt that
would not be available normally.

It is a minioncmd with no argument parser.

Access by typing tasker.py --power. This will begin the interactive prompt.
"""

import minioncmd

class PowerCmd(minioncmd.MinionCmd):
    """PluginCmd(name [,master, manager, completekey, stdin, stout])
    Poweruser interactive prompt commands.
    """

    prompt = "power> "
    doc_leader = "Power User Help"

    def do_qlist(self, line):
        """lists all items in the command queue"""
        if not self.master.cmdqueue:
            self.stdout.write("No Queued Commands\n")
        for item in self.master.cmdqueue:
            self.stdout.write("Queued Command: {}\n".format(item))

    def do_sections(self, line):
        """Lists the configparser sections"""
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

        except Exception as E:
            print(E)