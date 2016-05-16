# -*- coding: utf-8 -*-
"""
Created on Mon Feb 29 15:50:32 2016

@author: jenglish
"""
import logging

from yapsy.IPlugin import IPlugin


class BaseTaskerPlugin(IPlugin):
    _log = logging.getLogger('plugin')
    

class TaskerPlugin(BaseTaskerPlugin):
    pass

class NewCommandPlugin(BaseTaskerPlugin):
    pass


class SubCommandPlugin(BaseTaskerPlugin):
    pass
