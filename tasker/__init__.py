import sys

import cmd
from argparse import ArgumentParser

import tasker

lister = ArgumentParser("tasker")

lister.add_argument("-n", dest="by_pri", action='store_false', default=True, )
lister.add_argument("-f", dest="filters", default=[], nargs="*")
lister.add_argument("-a", dest="filterop", action='store_true', default=False,)
lister.add_argument("-u", dest="showuid", action="store_true", default=False)
lister.add_argument("-x", dest="showcomplete", action="store_true", default=False)


class Tasker(cmd.Cmd):
    intro = "Welcome to Tasker."
    prompt = '-> '

    def do_list(self, arg):
        """List tasks"""

        args =lister.parse_args(arg.split())
        tasker.list_tasks(**vars(args))

    def do_quit(self, arg):
        """Quits the interactive loop"""
        return  True

    def do_add(self, arg):
        print(tasker.add_task(arg))


if __name__ == '__main__':
    t = Tasker()
    if sys.argv[1] == 'interactive':
        t.cmdloop()
    else:
        t.onecmd(" ".join(sys.argv[1:]))

