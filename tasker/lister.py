# -*- coding: utf-8 -*-
"""
Created on Fri Mar 18 12:39:22 2016

@author: jenglish
"""
from __future__ import print_function


def print_list(things, headers):
    headers = [h.strip() for h in headers]
    lengths = [len(header) for header in headers]
    for thing in things:
        for idx, item in enumerate(thing):
            lengths[idx] = max(lengths[idx], len(item))
    # header_row = ' '.join(headers)
    for idx, header in enumerate(headers):
        print("{0:{1}} ".format(header, lengths[idx]), end='')
    print('')
    print(*['-' * l for l in lengths], sep=" ")
    for thing in things:
        for idx, item in enumerate(thing):
            print("{0:{1}} ".format(item, lengths[idx]), end='')
        print('')


if __name__ == '__main__':
    print_list(('Here 0 0'.split(), 'There 10 0'.split()),
               'Wh Open Closed'.split())
