# -*- coding: utf-8 -*-

from setuptools import setup

setup(name='t',
      version='1.0',
      description='Extensible command line todo-manager',
      url='https://github.com/JoshuaEnglish/tasker',
      author="Josh English",
      author_email="josh@joshuarenglish.com",
      license="GNU3",
      packages=["tasker", ],
      zip_safe=False, requires=['yapsy', 'colorama'])
