
"""
RegexPlugin

Twiddles its thumbs

Created on 2017-05-19T13:49:27.903602

@author: jenglish
"""
import argparse
import basetaskerplugin


class RegexPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Regex')
        # edit the following line
        self.setConfigOption('public_methods', 'do_Regex')

        
        # define argument parsers
        regex = argparse.ArgumentParser('regex')
       
       # add parsers

        self.parsers = {
            regex: "Thumb twiddlers",
        }

        super().activate()

    def do_Regex(self, text):
        """Thumb twiddler"""
        pass


