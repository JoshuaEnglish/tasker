# -*- coding: utf-8 -*-
"""
Created on Wed Jan 18 16:34:19 2017

@author: jenglish
"""

import re
import colorama

re_color = re.compile("""
(?P<style>bright|dim|normal|resetall)?\s*
(?P<fore>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow)?
(\s+on\s+(?P<back>black|blue|cyan|green|lightblack|magenta|red|reset|white|yellow))?
""", re.VERBOSE + re.IGNORECASE)

def get_color(text):
    stuff = re_color.match(text).groupdict()
    style = stuff.get('style') or  ''
    if style.upper() == 'RESETALL':
        style = 'RESET_ALL'

    fore = stuff.get('fore') or ''
    if fore.upper() == 'LIGHTBLACK':

        fore = 'LIGHTBLACK_EX'

    back = stuff.get('back') or ''
    if back.upper() == 'LIGHTBLACK':
        back = 'LIGHTBLACK_EX'

    res = []
    if style:
        res.append(getattr(colorama.Style, style.upper()))
    if fore:
        res.append(getattr(colorama.Fore, fore.upper()))
    if back:
        res.append(getattr(colorama.Back, back.upper()))
    return ''.join(res)




if __name__=='__main__':
    def test(color):
        tcolor=get_color(color)
        print(tcolor, repr(tcolor), color)
    test('bright red on green')
    test('lightblack on reset')
    test('WHITE on cyan')
    test('resetall')