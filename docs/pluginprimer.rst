Plugin Primer
=============

Tasker uses two kinds of interfaces. The first interface is the command line
that relies on argparse to check the line sent from the system. This line
is then fed to the underlying cmd.Cmd object.

Currenty the only command line actions that are supported are ``list``, ``do``,
and ``add``. Enter the interpretive prompt to access all the features tasker
offers.

Running ``tasker -i`` or ``tasker --interactive`` enters the interactive
prompt.

:class:`TaskerCmd` is built on top of :class:`BossCmd`, a tool that allows
to add subprograms (called *minions*) that provide more functionality. Minions
can be loaded through the plugin system.

:class:`BossCmd` describes a top-level interactive prompt. :class:`MinionCmd`
describes a subprogram at the interactive prompt. 

There are two ways to link a Minion to a Boss::

    Boss = BossCmd()

    # long way to add minion to boss
    Story = StoryCmd('story')
    Boss.add_minion('story', Story)

    # minions accept a boss
    Sub = SubmissionCmd('submission', Boss)
    Mark = MarketCmd('market', Boss)

The interactive prompt can move in and out of subprograms, and subprograms
can call eachother without stacking::

    >>> Boss.cmdloop()
    Boss> story
    story> submission
    submission> done
    Boss> 

All MinionCmd instances have a ``done`` command that exits the subpgram and
returns to the parent BossCmd instance. MinionCmd instances also have a 
``quit`` command that quits the program entirely.

If a MinionCmd instance can be called with a command, which will be executed,
then the program will return to the calling program::

    Boss> story help
    Help for StoryCmd
    Documented commands (type help <topic>):
    ========================================
    done  help  market  quit  submission
    
    Boss> submission
    submission> story help
    Help for StoryCmd
    Documented commands (type help <topic>):
    ========================================
    done  help  market  quit  submission
    
    submission>





