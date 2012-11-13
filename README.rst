python-sharepoint
=================

A Python library and command-line utility for gettting data out of SharePoint.


Installation
------------

Simply check out from https://github.com/ox-it/python-sharepoint and run::

   $ python setup.py install


Usage
-----

First, you need to create a ``SharePointSite`` object. We'll assume you're
using basic auth; if you're not, you'll need to create an appropriate `urllib2
Opener <http://docs.python.org/2/library/urllib2.html#urllib2.build_opener>`_
yourself.

.. code::

   from sharepoint import SharePointSite, basic_auth_opener

   server_url = "http://sharepoint.example.org/"
   site_url = server_url + "sites/foo/bar"

   opener = basic_auth_opener(server_url, "username", "password")

   site = SharePointSite(site_url, opener)


Lists
~~~~~

First, get a list of SharePoint lists available::

   for sp_list in site.lists:
       print sp_list.id, sp_list.meta['Title']

You can look up lists by ID, or by name::

   # By ID, without braces
   print site.lists['1EF5668C-0AB4-4020-98EF-26325E412C3C']
   # By ID, with braces
   print site.lists['1EF5668C-0AB4-4020-98EF-26325E412C3C']
   # By name
   print site.lists['ListName']

Given a list, you can iterate over its rows::

   sp_list = site.lists['ListName']
   for row in sp_list.rows:
       print row.id, row.FieldName

It's not yet possible to modify lists using this library.


Command-line utility
~~~~~~~~~~~~~~~~~~~~

Here's how to get a list of lists from a SharePoint site::

   $ sharepoint --site-url=http://sharepoint.example.org/sites/foo/bar \
                --username=username --password=password

And here's how to get an entire list as XML::

   $ sharepoint --site-url=http://sharepoint.example.org/sites/foo/bar \
                --list-name=ListName \
                --username=username --password=password

You can also specify a file containing username and password in the format
'username:password'::

   $ sharepoint --credentials=path/to/credentials [...]

For help, use ``-h``::

   $ sharepoint -h

