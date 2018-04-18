# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 12:39:22 2016

@author: jenglish
"""
from __future__ import print_function

import re

# https://stackoverflow.com/questions/2186919
# https://stackoverflow.com/questions/4963691
split_ANSI_escape_sequences = re.compile(r"""
    (?P<col>(\x1b\[[;\d]*[A-Za-z])*)(?P<text>.*)
    """, re.VERBOSE).match


def split_ANSI(s):
    return split_ANSI_escape_sequences(s).groupdict()


def print_list(things, headers):
    headers = [h.strip() for h in headers]
    lengths = [len(header) for header in headers]

    for thing in things:
        for idx, item in enumerate(thing):
            lengths[idx] = max(lengths[idx], len(split_ANSI(item)['text']))
    # header_row = ' '.join(headers)
    for idx, header in enumerate(headers):
        print("{0:{1}} ".format(header, lengths[idx]), end='')
    print('')
    print(*['-' * l for l in lengths], sep=" ")
    for thing in things:
        for idx, item in enumerate(thing):
            d = split_ANSI(item)
            col = d.get('col', '')
            text = d.get('text', 'OOPS!')

            print("{0}{1:{2}} ".format(col, text, lengths[idx]), end='')
        print('')


if __name__ == '__main__':
    import colorama
    colorama.init(autoreset=True)

    first = 'Here %s0 45' % (colorama.Fore.RED + colorama.Style.BRIGHT)
    last = "%sa 1 2" % (colorama.Style.RESET_ALL)
    print_list((first.split(), 'There 10 0'.split(), last.split()),
               'Wh Open Closed'.split())

    print(split_ANSI('text a'))
    print(split_ANSI('\x1b[31mtext x'))
    print(split_ANSI('\x1b[31m\x1b[1mtext b'))
