# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 11:49:57 2016

@author: jenglish
"""
import sys
import os
from configparser import ConfigParser

import logging

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m%d %I:%M:%S %p')
logging.getLogger('yapsy').setLevel(logging.DEBUG)

import yapsy.ConfigurablePluginManager

config = ConfigParser()
config.read_dict({'Files': {'tasker-dir': os.path.join(os.environ['APPDATA'], 'tasker'),
                            'task-path': "%(tasker-dir)s/todo.txt",
                            'done-path': "%(tasker-dir)s/done.txt",
                            },
                  'Tasker': {'hidden_extensions': 'uid'}})

if hasattr(sys, "frozen"):
    configdir = os.path.dirname(sys.executable)
else:
    configdir = os.path.dirname(__file__)

configpath = os.path.join(configdir, 'tasker.ini')

config.read(configpath)

def save_config():
    with open(configpath,'w') as fp:
        config.write(fp)

class SingleFileAnalyzer(yapsy.PluginFileLocator.PluginFileAnalyzerMathingRegex):
    def getInfosDictFromPlugin(self, dirpath, filename):
        """
        Returns the extracted plugin informations as a dictionary.
        This function ensures that "name" and "path" are provided.
        """
        # use the filename alone to extract minimal informations.
        # do not import the file, but it okay to read
        infos = {}
        module_name = os.path.splitext(filename)[0]
        plugin_filename = os.path.join(dirpath,filename)
        if module_name == "__init__":
            module_name = os.path.basename(dirpath)
            plugin_filename = dirpath
        infos["name"] = "%s" % module_name
        infos["path"] = plugin_filename
        cf_parser = ConfigParser()
        cf_parser.add_section("Core")
        cf_parser.set("Core","Name",infos["name"])
        cf_parser.set("Core","Module",infos["path"])
        
        # must return these at minimum
        # return None, cf_parser if plugin doesn't validate
        return infos,cf_parser
    
manager = yapsy.ConfigurablePluginManager.ConfigurablePluginManager(config)
locator = yapsy.PluginFileLocator.PluginFileLocator(
    [SingleFileAnalyzer('Singlefile', r'.+Plugin.py$'),]
    )
manager.setPluginLocator(locator)
manager.setPluginPlaces(['plugins',])



