
"""
WebserverPlugin

Twiddles its thumbs

Created on 2017-01-30T13:15:35.743699

@author: jenglish
"""
import os
import argparse
import re

from bottle import Bottle, run, TEMPLATE_PATH, static_file, request, redirect
from bottle import jinja2_view as view, jinja2_template as template

import basetaskerplugin

VIEWS = os.path.join(os.path.dirname(__file__), 'views')
STATIC = os.path.join(os.path.dirname(__file__), 'static')
TEMPLATE_PATH.insert(0, STATIC)
TEMPLATE_PATH.insert(0, VIEWS)

app = Bottle()

re_pri = re.compile(r"~?\(([A-Z])\)")
re_context = re.compile(r"\s([@][-\w]+)")
re_project = re.compile(r"\s([+][-\w]+)")

@app.route('/static/tasker.css')
def css():
    return static_file('tasker.css', root=STATIC)

@app.route('/')
def home():
    return f"Tasker on the Web with {app.tasklib}"

def prep_tasks():
    tasks = app.tasklib.sort_tasks()
    priorities = set()
    contexts = set()
    projects = set()
    for idx, task in tasks:
        contexts.update(task.contexts)
        projects.update(task.projects)
        priorities.add(task.priority)
    return (tasks, priorities, projects, contexts)

@app.route('/tasks')
def tasks():
    tasks, priorities, projects, contexts = prep_tasks()
    return template(
        'tasklist.html', 
        tasks=tasks,
        priorities=list(sorted(priorities)),
        contexts=list(sorted(contexts)),
        projects=list(sorted(projects))
        )

@app.route('/tasks', method="POST")
def tasks():
    tasks, priorities, projects, contexts = prep_tasks()
    #override tasks by applying filters
    pri = request.forms.get('pri')
    project = request.forms.get('project')
    context = request.forms.get('context')
    text = request.forms.get('text')
    filters = []
    if pri:
        filters.append(f"({pri})")
    if project:
        filters.append(project)
    if context:
        filters.append(context)
    if text:
        filters.append(text)
    tasks = app.tasklib.sort_tasks(filters=filters)

    return template(
        'tasklist.html', 
        tasks=tasks,
        priorities=list(sorted(priorities)),
        contexts=list(sorted(contexts)),
        projects=list(sorted(projects))
        )


@app.route('/newtask', method="POST")
def addtask():
    text = request.forms.get('tasktext')
    print('text from form:', text)
    if text:
        res, newtext = app.tasklib.add_task(text)
    redirect('/tasks')

@app.route('/dotask/<num:int>')
def dotask(num):
    tasks = app.tasklib.sort_tasks()
    text = [t for n,t in tasks if n==num][0]
    return template(
        'dotask.html',
        idx=num,
        text=text)

@app.route('/do', method="POST")
def completetask():
    tasknum = request.forms.get('tasknum')
    comment = request.forms.get('comment')
    res, text = app.tasklib.complete_task(int(tasknum), comment) 
    print(res, text)
    redirect('/tasks')


class WebserverPlugin(basetaskerplugin.NewCommandPlugin):
    def activate(self):
        self._log.debug('Activating Webserver')
        # edit the following line
        self.setConfigOption('public_methods', 'do_webserver')


        # define argument parsers
        webserver = argparse.ArgumentParser('webserver')
        webserver.add_argument('-p', '--port', type=int, default=5000,
                               help="Port to serve pages")
        webserver.add_argument('--no-launch', action='store_false',
                               dest='launch', default=True,
                               help="Do not launch web browser automatically")

        # add parsers

        self.parsers = {
            webserver: "Launch a webserver interface",
        }

        super().activate()

    def do_webserver(self, text):
        """Thumb twiddler"""
        app.tasklib = self.lib 
        run(app, host='localhost', port=8080, debug=True, reloader=True)




