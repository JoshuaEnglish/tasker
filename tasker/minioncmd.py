# -*- coding: utf-8 -*-
"""
MinionCmd

This module defines two subclasses of the cmd.Cmd class.

:class:`BossCmd` is for the top level command line interpreter.
:class:`MinionCmd` is for sub programs that have their own prompts and command
structure. MinionCmd instances can transfer control to other instances, or
return to the main BossCmd instance.
"""

import cmd 
import logging

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s: %(message)s",
                    datefmt="%Y-%m-%d %I:%M:%S %p")
#logging.getLogger('bosscmd').setLevel(logging.DEBUG)
#logging.getLogger('minioncmd').setLevel(logging.DEBUG)


class BossCmd(cmd.Cmd):
    """BossCmd
    Command line tool for managing subprograms.
    """

    #: logging.logger object called 'bosscmd'
    _log = logging.getLogger('bosscmd')

    prompt = 'Boss> '

    def __init__(self): 
        super().__init__(self)
        self.exit_called_from_minion = False

        #: Dictionary of minion_name: MinionCmd instance
        self.minions = {}

        #: Dictionary of minion name: switch_to_minion function calls to be
        #: dynamically applied to minions
        self.switchers = {}

        self.doc_leader = "Help for BossCmd"

    def add_minion(self, name, cmder):
        self._log.debug("Adding minion %s", name)
        self.minions[name] = cmder

        if not hasattr(cmder, 'master'):
            cmder.master = None
        cmder.master = self


        # step one: create a "do_" method to access the minion
        def do_minion(self, arg):
            self._log.debug("Calling minion %s with %s",name,  arg)
            if arg:
                cmder.onecmd(arg)
            else:
                cmder.cmdloop()

        do_minion.__doc__ = "Send a single command to the {} subprogram or start its loop.".format(name)

        setattr(self.__class__, "do_{}".format(name), do_minion)

        # step two: create the switch methods between minions
        # the first minion doesn't need any switch methods
        # the second minion needs a switch to the first, and the first needs a switch to the second
        # the third minion needs a switch to the first and second, the first to the third, and the second to the third
        # this means it may be wiser to build a dictionary of switch methods
        # when adding a minion, create a switch method to go to that minion
        self._log.debug('Creating Switch to minion for %s', name)

        def switch_to_minion(self, line):
            if line:

                self._log.debug("Calling co-minion with line %s", line)
                self.master.minions[name].onecmd(line)
                self._log.debug("Adding switch back to master.cmdqueue")
                self.master.cmdqueue.append(self.name)
            else:
                self._log.debug("Adding co-minon command to master.cmdqueue")
                self.master.cmdqueue.append('{} {}'.format(name, line))
            return True

        switch_to_minion.__doc__ = "Send a single command to the {} subprogram or begin its loop".format(name)

        self.switchers[name] = switch_to_minion

        for switch in self.switchers:
            for minion in self.minions:
                if switch == minion:
                    continue
                self._log.debug('Add switch to %s to %s', switch, minion)
                setattr(self.minions[minion].__class__, "do_{}".format(switch), self.switchers[switch])

    def do_quit(self, line):
        "Quits the program"
        return True 
    
    def postloop(self): 
        pass
    
    def postcmd(self, stop, line): 
        # check if minion called for exit 
        if self.exit_called_from_minion: 
            stop = True 
        return stop 

    def onecmd(self, line):
        stop = super().onecmd( line)
        while len(self.cmdqueue):
            text = self.cmdqueue.pop(0)
            #self.cmdqueue = self.cmdqueue[1:]
            #print('postcmd: {}'.format(text))
            self._log.debug("Processing queued command: %s", text)
            stop = self.onecmd(text)
        return stop

    def do_qlist(self, line):
        """lists all items in the command queue"""
        for item in self.cmdqueue:
            print("Queued Command: {}".format(item))

class MinionCmd(cmd.Cmd):
    _log = logging.getLogger('minioncmd')

    def __init__(self, name, master=None):
        super().__init__(self)
        self.prompt = "{}> ".format(name)
        self.name = name
        self.master = master
        if self.master:
            self.master.add_minion(name, self)
            
    def do_quit(self, line):
        """Exits the entire program"""
        if self.master:
            self.master.exit_called_from_minion = True 
        return True 
    
    def do_done(self, line): 
        """Exits the sub program and returns to the main program"""
        return True


if __name__=='__main__':
    class SubmissionCmd(MinionCmd):
        doc_leader = "Help for SubmissionCmd"


    class StoryCmd(MinionCmd):
        doc_leader = "Help for StoryCmd"


    class MarketCmd(MinionCmd):
        doc_leader = "Help for MarketCmd"

        def do_hello(self, line):
            print("Hello to {} from Market".format(line))
            self.master.cmdqueue.append('goodbye cruel world')

    Boss = BossCmd()

    # long way to add minion to boss
    Story = StoryCmd('story')
    Boss.add_minion('story', Story)

    # minions accept a boss
    Sub = SubmissionCmd('submission', Boss)
    Mark = MarketCmd('market', Boss)

    Boss.onecmd('story market hello from onecmd')

    Boss.onecmd('market submission see ya! from onecmd')