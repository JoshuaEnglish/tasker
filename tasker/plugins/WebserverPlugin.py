
"""
WebserverPlugin

Twiddles its thumbs

Created on 2017-01-30T13:15:35.743699

@author: jenglish
"""
import os
import argparse

import bottle

import basetaskerplugin

VIEWS = os.path.join(os.path.dirname(__file__), 'views')
STATIC = os.path.join(os.path.dirname(__file__), 'static')

class WebserverPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Webserver')
        # edit the following line
        self.setConfigOption('public_methods', 'do_webserver')


        # define argument parsers
        webserver = argparse.ArgumentParser('webserver')
        webserver.add_argument('-p', '--port', type(int), default=5000,
                               help="Port to serve pages")
        webserver.add_argument('--no-launch', action='store_false',
                               dest='launch', default=True,
                               help="Do not launch web browser automatically")

        # add parsers

        self.parsers = {
            webserver: "Thumb twiddlers",
        }

        super().activate()

    def do_webserver(self, text):
        """Thumb twiddler"""
        pass




