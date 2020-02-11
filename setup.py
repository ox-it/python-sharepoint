from distutils.core import setup

__version__ = '0.4.2'

packages = ['sharepoint',
            'sharepoint.lists']

setup(name='sharepoint',
      description='Module and command-line utility to get data out of SharePoint',
      long_description=open('README.rst').read(),
      author='IT Services, University of Oxford',
      author_email='opendata@oucs.ox.ac.uk',
      version=__version__,
      packages=packages,
      scripts=['bin/sharepoint'],
      url='https://github.com/ox-it/python-sharepoint',
      license='BSD-3-Clause',
      classifiers=['Development Status :: 4 - Beta',
                   'Environment :: Console',
                   'Intended Audience :: System Administrators',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Information Technology',
                   'Operating System :: OS Independent',
                   'Topic :: Internet :: WWW/HTTP',
                   'Topic :: Office/Business :: Groupware'],
      keywords=['SharePoint'],
      install_requires=['lxml', 'six'])

