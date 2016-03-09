from setuptools import setup


def readme():
    with open("README.rst") as f:
        return f.read()

setup(name='tasker',
      version='0.1',
      description="Extensible text-based todo manager",
      long_description=readme(),
      classifiers=[
          "Programming Language :: Python :: 3",
          "Development Status :: 3 - Alpha",
          "Intended Audience :: End Users/Desktop",
          "Natural Language :: English",

      ],
      url='http://github.com/JoshuaEnglish/tasker',
      author="Joshua R English",
      author_email="Josh@JoshuaREnglish.com",
      license="BFD",
      packages=["tasker",],
      install_requires = [
        'yapsy', 'pypubsub',
          ],
      zip_safe=False,
      )