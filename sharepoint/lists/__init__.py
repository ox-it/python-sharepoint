import re
import urllib2
import urlparse

from lxml import etree

from sharepoint.xml import SP, namespaces
from sharepoint.lists.types import type_mapping, default_type

uuid_re = re.compile(r'^\{?([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})\}?$')

class SharePointLists(object):
    def __init__(self, site, url, post):
        self.site = site
        self.url = url + '_vti_bin/Lists.asmx'
        self.post = post

    @property
    def all_lists(self):
        if not hasattr(self, '_all_lists'):
            xml = SP.GetListCollection()
            result = self.post(self.url, xml)
    
            self._all_lists = []
            for list_element in result.xpath('sp:GetListCollectionResult/sp:Lists/sp:List', namespaces=namespaces):
                self._all_lists.append(SharePointList(self.site, self.url, self.post, self, dict(list_element.attrib)))
        return self._all_lists

    def __iter__(self):
        return iter(self.all_lists)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.all_lists[key]
        elif uuid_re.match(key.lower()):
            key = '{0}'.format(uuid_re.match(key.lower()).group(0))
            for list_object in self.all_lists:
                if list_object.id == key:
                    return list_object
            raise KeyError('No list with ID {0}'.format(key))
        elif isinstance(key, basestring):
            for list_object in self.all_lists:
                if list_object.meta['Title'] == key:
                    return list_object
            raise KeyError("No list with title '{0}'".format(key))
        raise KeyError

class SharePointList(object):
    def __init__(self, site, url, post, lists, meta):
        self.site = site
        self.url, self.post, self.lists, self.meta = url, post, lists, meta
        self.id = meta['ID'].lower()

    def __repr__(self):
        return "<SharePointList {0} '{1}'>".format(self.id, self.meta['Title'])

    @property
    def settings(self):
        if not hasattr(self, '_settings'):
            xml = SP.GetList(SP.listName('{0}'.format(self.id)))
            response = self.post(self.url, xml)
            self._settings = response[0][0]
        return self._settings

    @property
    def rows(self):
        if not hasattr(self, '_rows'):
            xml = SP.GetListItems(SP.listName('{0}'.format(self.id)))
            response = self.post(self.url, xml)
            xml_rows = list(response[0][0][0])
            self._rows = []
            for xml_row in xml_rows:
                self._rows.append(self.row_class(xml_row))
        return self._rows

    @property
    def rows_by_id(self):
        if not hasattr(self, '_rows_by_id'):
            self._rows_by_id = {}
            for row in self.rows:
                self._rows_by_id[row.id] = row
        return self._rows_by_id

    @property
    def fields(self):
        if not hasattr(self, '_fields'):
            self._fields = []
            for field in self.settings.xpath('sp:Fields/sp:Field', namespaces=namespaces):
                field_class = type_mapping.get(field.attrib['Type'], default_type)
                self._fields.append(field_class(self.lists, self.id, field))
        return self._fields

    @property
    def row_class(self):
        if not hasattr(self, '_row_class'):
            attrs = {'fields': self.fields, 'list': self}
            for field in self.fields:
                attrs[field.name] = field.descriptor
            self._row_class = type('SharePointListRow', (SharePointListRow,), attrs)
        return self._row_class

class SharePointListRow(object):
    def __init__(self, row):
        self.data = {}
        for field in self.fields:
            value = field.get(row)
            if value is not None:
                self.data[field.name] = value
        self.id = self.ID

    def __repr__(self):
        return "<SharePointListRow {0} '{1}'>".format(self.id, self.Title)

    @property
    def is_file(self):
        return hasattr(self, 'LinkFilename')

    def open(self):
        url = urlparse.urljoin(self.list.site.url,
                               self.list.meta['Title'] + '/' + self.LinkFilename.replace(' ', '%20'))
        request = urllib2.Request(url)
        request.add_header('Translate', 'f')
        return self.list.site.opener.open(request)

