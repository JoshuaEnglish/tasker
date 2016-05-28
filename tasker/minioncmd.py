# -*- coding: utf-8 -*-
"""
minioncmd
=========

This module defines two subclasses of the cmd.Cmd class.

:class:`BossCmd` is for the top level command line interpreter.
:class:`MinionCmd` is for sub programs that have their own prompts and command
structure. MinionCmd instances can transfer control to other instances, or
return to the main BossCmd instance.

Both :class:`BossCmd` and :class:`MinionCmd` inherit from :class:`ExtHelpCmd`
which enhances the basic :meth:`~ExtHelpCmd.do_help` method.

"""

import cmd 
import logging


class ExtHelpCmd(cmd.Cmd):
    """ExtHelpCmd
    
    Extended Help Cmd. Subclass of cmd.Cmd that creates an extra layer
    of topics to refer to minions in a separate topic group.
    """

    minion_header = "Minion commands (type <command> help)"
    doc_header = "Local commands (type help <command>)"
    
    def do_help(self, arg):
        """List available commands with "help" or detailed help with "help cmd"."""
        if arg:
            # XXX check arg syntax
            try:
                func = getattr(self, 'help_' + arg)
            except AttributeError:
                try:
                    doc=getattr(self, 'do_' + arg).__doc__
                    if doc:
                        self.stdout.write("%s\n"%str(doc))
                        return
                except AttributeError:
                    pass
                self.stdout.write("%s\n"%str(self.nohelp % (arg,)))
                return
            func()
        else:
            names = self.get_names()
            cmds_doc = []
            minion_doc = []
            if hasattr(self, 'minions'):
                minions = self.minions.keys()
            elif hasattr(self, 'master'):
                if self.master is not None:
                    minions = self.master.minions.keys()
                else:
                    minions = []
            cmds_undoc = []
            misc = {}
            for name in names:
                if name[:5] == 'help_':
                    misc[name[5:]]=1
            names.sort()
            # There can be duplicates if routines overridden
            prevname = ''
            for name in names:
                if name[:3] == 'do_':
                    if name == prevname:
                        continue
                    prevname = name
                    cmd=name[3:]
                    if cmd in misc:
                        if cmd in minions:
                            minion_doc.append(cmd)
                        else:
                            cmds_doc.append(cmd)
                        del misc[cmd]
                    elif getattr(self, name).__doc__:
                        if cmd in minions:
                            minion_doc.append(cmd)
                        else:
                            cmds_doc.append(cmd)
                    else:
                        cmds_undoc.append(cmd)
            
            cmds_sys = []
            for cmd in ['help','quit','done']:
                if cmd in cmds_doc:
                    cmds_doc.remove(cmd)
                    cmds_sys.append(cmd)
            
            cmds_sys.sort()
                        
            self.stdout.write("%s\n"%str(self.doc_leader))
            self.print_topics(self.doc_header,   cmds_doc,   15, 80)
            self.print_topics(self.minion_header, minion_doc, 15, 80)
            self.print_topics("Program control commands", cmds_sys, 15, 80)
            self.print_topics(self.misc_header,  list(misc.keys()), 15, 80)
            self.print_topics(self.undoc_header, cmds_undoc, 15, 80)

class BossCmd(ExtHelpCmd):
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
        """Sets the instance ``inloop`` property to ``False``"""
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
        """Quits the program"""
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
        self.process_queue()
#        while len(self.cmdqueue):
#            text = self.cmdqueue.pop(0)
#            self._log.debug("Processing queued command: %s", text)
#            self.onecmd(text)
        return stop

    def process_queue(self):
        while len(self.cmdqueue):
            text = self.cmdqueue.pop(0)
            self._log.debug("Processing queued command: %s", text)
            self.onecmd(text)



class MinionCmd(ExtHelpCmd):
    """MinionCmd

    The MinionCmd object provides methods for connecting minions to the boss.

    """
    _log = logging.getLogger('minioncmd')
    doc_leader = "Help for MinionCmd"
    minion_header = "Other minions (type <topic> help)"

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
 
    def onecmd(self, line):
        """Process a single command and process the cmdqueue
        :rtype: boolean
        """
        stop = super().onecmd( line)
        self.master.process_queue()
#        while len(self.cmdqueue):
#            text = self.cmdqueue.pop(0)
#            self._log.debug("Processing queued command: %s", text)
#            self.onecmd(text)
        return stop
        
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
            self.master.cmdqueue.append('push hello from Market!')

    class LocalBully(BossCmd):
        doc_leader = "Help for the Bully"
        
        def do_push(self, line):
            print("BullyBoy pushes:", line)
            
    Boss = LocalBully()

    # long way to add minion to boss
    Story = StoryCmd('story')
    Boss.add_minion('story', Story)

    # minions accept a boss
    Sub = SubmissionCmd('submission', Boss)
    Mark = MarketCmd('market', Boss)

    Boss.onecmd('story market hello onecmd')
