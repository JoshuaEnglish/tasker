# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 10:29:54 2016

@author: jenglish
"""
import argparse


def add_core_subparsers(commands):
    list_parser = commands.add_parser('list', help='list tasks',
                                      description="Tool for listing tasks",
                                      )
    list_parser.add_argument('-n', action="store_false",
                             dest="by_pri", default=True,
                             help="Prints task list in numerical order, otherwise orders by priority")
    list_parser.add_argument('-f', dest="filters", nargs="*",
                             help="Only lists tasks containing these words")
    list_parser.add_argument('-y', dest="filterop", action="store_true",
                             default=False,
                             help="Shows tasks matching any filter word. Default is to match all")
    list_parser.add_argument('-a', dest="showcomplete", action="store_true",
                             default=False,
                             help="Show completed (but not archived) tasks.")
    list_parser.add_argument('-x', dest="showext", action="store_true",
                             default=False,
                             help="Shows hidden text extensions")

    add_parser = commands.add_parser('add', help="add a task")
    add_parser.add_argument(nargs="+", dest="text",
                            help="text of the new task")

    do_parser = commands.add_parser('do', help="mark a task as complete")
    do_parser.add_argument('tasknum', type=int,
                           help="number of the task to complete")
    do_parser.add_argument('comment', nargs=argparse.REMAINDER,
                           help="comment to add to the completed task")

    priority_parser = commands.add_parser('pri', help="prioritize a task")
    priority_parser.add_argument('tasknum', type=int,
                                 help="number of the task to prioritize")
    priority_parser.add_argument('priority', type=str,
                                 help="letter of new priority or _ to clear")
    priority_parser.add_argument('note', nargs=argparse.REMAINDER,
                                 help="optional note to attach to task")


