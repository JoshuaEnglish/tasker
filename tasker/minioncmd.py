# -*- coding: utf-8 -*-
"""

This module defines two subclasses of the cmd.Cmd class.

:class:`BossCmd` is for the top level command line interpreter.
:class:`MinionCmd` is for sub programs that have their own prompts and command
structure. MinionCmd instances can transfer control to other instances, or
return to the main BossCmd instance.

"""

import cmd 
import logging

logging.basicConfig(format="%(asctime)s %(name)s %(levelname)s: %(message)s in %(module)s:%(funcName)s",
                    datefmt="%Y-%m-%d %I:%M:%S %p")


class BossCmd(cmd.Cmd):
    """BossCmd
    Command line tool for managing subprograms.
    """

    #: logging.logger object called 'bosscmd'
    _log = logging.getLogger('bosscmd')

    prompt = 'Boss> '
    doc_leader = "Help for BossCmd"

    def __init__(self, completekey='tab', stdin=None, stdout=None): 
        super().__init__(completekey, stdin, stdout)
        
        #: Flag to detect when minions call to quit the program
        self.exit_called_from_minion = False
        
        #: flag to determine if the BossCmd instance is in the middle of a
        #: loop or not (if not, assume a call to onecmd)
        self.inloop = False

        #: Dictionary of minion_name: MinionCmd instance
        self.minions = {}

        #: Dictionary of minion name: switch_to_minion function calls to be
        #: dynamically applied to minions
        self.switchers = {}


    def preloop(self):
        """Sets the instance ``inloop`` property to ``True``"""
        self.inloop = True
        super().preloop()

    def postloop(self):
        """Sets the instance ``inloop`` property to ``Fales``"""
        self.inloop = False
        super().postloop()
        
    def default(self, line):
        """Called on an input line when the command prefix is not recognized.

        If this method is not overridden, it prints an error message and
        returns.

        """
        self.stdout.write('*** Unknown %s syntax: %s\n' % 
            (self.__class__.__name__, line))
        
    def add_minion(self, name, cmder):
        """add_minion(name, minion)
        
        Adds the minion to the current instance of BossCmd. This method
        can be called automatically when creating an instance of MinionCmd.
        """
        self._log.debug("Adding minion %s", name)
        if not isinstance(cmder, MinionCmd):
            self._log.error('Cannot add %s, not MinionCmd instance', name)
            return None

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

        
        self._log.debug('Creating Switch to minion for %s', name)


        # step two: create a "do_" method for the minions
        def switch_to_minion(self, line):
            if line:

                self._log.debug("Calling co-minion with line %s", line)
                self.master.minions[name].onecmd(line)
                
                if self.master.inloop:
                    self._log.debug("Adding switch back to master.cmdqueue")
                    self.master.cmdqueue.append(self.name)
                    
            else:
                self._log.debug("Adding co-minon command to master.cmdqueue")
                self.master.cmdqueue.append('{} {}'.format(name, line))
                
            return True
        
        switch_to_minion.__name__ = "do_%s" % name
        switch_to_minion.__doc__ = "Send a single command to the {} subprogram or begin its loop".format(name)

        self.switchers[name] = switch_to_minion

        for switch in self.switchers:
            for minion in self.minions:
                if switch == minion:
                    continue
                self._log.debug('Adding do_%s to %s', switch, minion)
                setattr(self.minions[minion].__class__, "do_{}".format(switch), self.switchers[switch])

        return cmder

    def do_quit(self, line):
        "Quits the program"
        return True 
     
    def postcmd(self, stop, line): 
        # check if minion called for exit 
        if self.exit_called_from_minion: 
            stop = True 
        return stop 

    def onecmd(self, line):
        """Process a single command and process the cmdqueue
        :rtype: boolean
        """
        stop = super().onecmd( line)
        while len(self.cmdqueue):
            text = self.cmdqueue.pop(0)
            self._log.debug("Processing queued command: %s", text)
            self.onecmd(text)
        return stop



class MinionCmd(cmd.Cmd):
    """MinionCmd

    The MinionCmd object provides methods for connecting minions to the boss.

    """
    _log = logging.getLogger('minioncmd')
    doc_leader = "Help for MinionCmd"

    def __init__(self, name, master=None, 
                 completekey='tab', stdin=None, stdout=None):
        super().__init__(completekey, stdin, stdout)
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

    def default(self, line):
        """Called on an input line when the command prefix is not recognized.

        If this method is not overridden, it prints an error message and
        returns.

        """
        self.stdout.write('*** Unknown %s syntax: %s\n'% (self.__class__.__name__, line))

if __name__=='__main__':
    #logging.getLogger('bosscmd').setLevel(logging.DEBUG)
    #logging.getLogger('minioncmd').setLevel(logging.DEBUG)
    
    
    class SubmissionCmd(MinionCmd):
        doc_leader = "Help for SubmissionCmd"


    class StoryCmd(MinionCmd):
        doc_leader = "Help for StoryCmd"


    class MarketCmd(MinionCmd):
        doc_leader = "Help for MarketCmd"

        def do_hello(self, line):
            print("Hello to '{}' from Market".format(line))
            self.master.cmdqueue.append('qlist')

    Boss = BossCmd()

    # long way to add minion to boss
    Story = StoryCmd('story')
    Boss.add_minion('story', Story)

    # minions accept a boss
    Sub = SubmissionCmd('submission', Boss)
    Mark = MarketCmd('market', Boss)

    Boss.onecmd('story market hello from onecmd')
