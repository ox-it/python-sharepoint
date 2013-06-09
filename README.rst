python-sharepoint
=================

A Python library and command-line utility for gettting data out of SharePoint.

If you're more a Perl person, you might also want to try `SharePerltopus
<https://github.com/cgutteridge/SharePerltopus>`_.


Installation
------------

Either install the latest development from ``git``::

   $ git clone git://github.com/ox-it/python-sharepoint.git
   $ cd python-sharepoint
   $ sudo python setup.py install

... or, install the latest stable version using ``pip``::

   $ pip install sharepoint

You will need `lxml <http://lxml.de/>`_, which you can install using your
package manager or ``pip``. Run one of the following if it's not already
installed::

   $ sudo apt-get install python-lxml  # Debian, Ubuntu
   $ sudo yum install python-lxml      # RedHat, Fedora
   $ sudo pip install lxml             # pip


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
   print site.lists['{1EF5668C-0AB4-4020-98EF-26325E412C3C}']
   # By name
   print site.lists['ListName']

Given a list, you can iterate over its rows::

   sp_list = site.lists['ListName']
   for row in sp_list.rows:
       print row.id, row.FieldName

``rows`` is a list, which doesn't help you if you want to find rows by their
SharePoint row IDs. For this use a list's ``rows_by_id`` attribute, which
contains a mapping from row ID to row.

You can assign to fields as one would expect. Values will be coerced in
mostly-sensible ways. Once you're done, you'll want to sync your changes
using the list's ``save()`` method::

   sp_list = site.lists['ListName']
   
   # Set both the URL and the text
   sp_list.rows[5].Web_x0020_site = {'url': 'http://example.org/',
                                     'text': 'Example Website'}
   # Set the URL; leave the text blank
   sp_list.rows[6].Web_x0020_site = 'http://example.org/'
   # Clear the field
   sp_list.rows[7].Web_x0020_site = None
   
   sp_list.save()

Consult the ``descriptor_set()`` methods in ``sharepoint.lists.types`` module
for more information about setting SharePoint list fields.


Document libraries
~~~~~~~~~~~~~~~~~~

Support for document libraries is limited, but ``SharePointListRow`` objects do
support a ``is_file()`` method and an ``open()`` method for accessing file
data.


Command-line utility
~~~~~~~~~~~~~~~~~~~~

Here's how to get a list of lists from a SharePoint site::

   $ sharepoint lists -s http://sharepoint.example.org/sites/foo/bar \
                -u username -p password

And here's how to get one or more lists as XML::

   $ sharepoint exportlists -s http://sharepoint.example.org/sites/foo/bar \
                -l FirstListName -l "Second List Name" \
                -u username -p password

You can also specify a file containing username and password in the format
'username:password'::

   $ sharepoint --credentials=path/to/credentials [...]

If you want to manipulate SharePoint sites from a Python shell, use the
``shell`` command::

   $ sharepoint shell -s http://sharepoint.example.org/sites/foo/bar \
                -u username -p password


Once you're in the Python shell, there will be a ``site`` variable for the
site you specified. See above for things to do with your site.

For help (including to see more options to configure the output, use ``-h``::

   $ sharepoint -h

