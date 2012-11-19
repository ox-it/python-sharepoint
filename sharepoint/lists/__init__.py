import re
import urllib
import urllib2
import urlparse

from lxml import etree
from lxml.builder import E

from sharepoint.xml import SP, namespaces, OUT
from sharepoint.lists.types import type_mapping, default_type

uuid_re = re.compile(r'^\{?([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})\}?$')

LIST_WEBSERVICE = '_vti_bin/Lists.asmx'

class SharePointLists(object):
    def __init__(self, opener):
        self.opener = opener

    @property
    def all_lists(self):
        if not hasattr(self, '_all_lists'):
            xml = SP.GetListCollection()
            result = self.opener.post_soap(LIST_WEBSERVICE, xml)
    
            self._all_lists = []
            for list_element in result.xpath('sp:GetListCollectionResult/sp:Lists/sp:List', namespaces=namespaces):
                self._all_lists.append(SharePointList(self.opener, self, dict(list_element.attrib)))
        return self._all_lists

    def __iter__(self):
        return iter(self.all_lists)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.all_lists[key]
        elif uuid_re.match(key.lower()):
            # Using group 1 and adding braces allows us to match IDs that
            # didn't originally have braces.
            key = '{' + '{0}'.format(uuid_re.match(key.lower()).group(1)) + '}'
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

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        else:
            return True

    def as_xml(self, keys=None, **kwargs):
        if keys is not None:
            lists = (self[key] for key in keys)
        else:
            lists = self
        return OUT.lists(*[l.as_xml(**kwargs) for l in lists])

class SharePointList(object):
    def __init__(self, opener, lists, meta):
        self.opener = opener
        self.lists, self.meta = lists, meta
        self.id = meta['ID'].lower()
        self._deleted_rows = set()

    def __repr__(self):
        return "<SharePointList {0} '{1}'>".format(self.id, self.meta['Title'])

    @property
    def name(self):
        return self.meta['Title']

    @property
    def settings(self):
        if not hasattr(self, '_settings'):
            xml = SP.GetList(SP.listName(self.id))
            response = self.opener.post_soap(LIST_WEBSERVICE, xml)
            self._settings = response[0][0]
        return self._settings

    @property
    def rows(self):
        if not hasattr(self, '_rows'):
            xml = SP.GetListItems(SP.listName(self.id))
            response = self.opener.post_soap(LIST_WEBSERVICE, xml)
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
            attrs = {'fields': self.fields, 'list': self, 'opener': self.opener}
            for field in self.fields:
                attrs[field.name] = field.descriptor
            self._row_class = type('SharePointListRow', (SharePointListRow,), attrs)
        return self._row_class

    def as_xml(self, include_data=True, include_field_definitions=True, **kwargs):
        list_element = OUT('list', name=self.name, id=self.id)

        if include_field_definitions:
            fields_element = OUT('fields')
            for field in self.fields:
                field_element = OUT('field',
                                  name=field.name,
                                  display_name=field.display_name,
                                  sharepoint_type=field.sharepoint_type,
                                  type=field.type_name,
                                  **field.extra_field_definition())
                if field.description:
                    field_element.attrib['description'] = field.description
                field_element.attrib['multi'] = 'true' if field.multi else 'false'
                fields_element.append(field_element)
            list_element.append(fields_element)

        if include_data:
            rows_element = OUT('rows')
            for row in self.rows:
                rows_element.append(row.as_xml(**kwargs))
            list_element.append(rows_element)
        return list_element

    def append(self, data={}):
        """
        Appends a row to the list. Takes a dictionary, returns a row.
        """
        row = self.row_class()
        for key in data:
            setattr(row, key, data[key])
        self._rows.append(row)
        return row

    def remove(self, row):
        """
        Removes the row from the list.
        """
        self._rows.remove(row)
        self._deleted_rows.add(row)

    def save(self):
        """
        Updates the list with changes.
        """
        # Based on the documentation at
        # http://msdn.microsoft.com/en-us/library/lists.lists.updatelistitems%28v=office.12%29.aspx

        # Note, this ends up un-namespaced. SharePoint doesn't care about
        # namespaces on this XML node, and will bork if any of these elements
        # have a namespace prefix. Likewise Method and Field in
        # SharePointRow.get_batch_method().
        batches = E.Batch(ListVersion='1', OnError='Continue')
        # Here's the root element of our SOAP request.
        xml = SP.UpdateListItems(SP.listName(self.id), SP.updates(batches))

        # rows_by_batch_id contains a mapping from new rows to their batch
        # IDs, so we can set their IDs when they are returned by SharePoint.
        rows_by_batch_id, batch_id = {}, 1

        for row in self._rows:
            batch = row.get_batch_method()
            if batch is None:
                continue
            # Add the batch ID
            batch.attrib['ID'] = unicode(batch_id)
            rows_by_batch_id[batch_id] = row
            batches.append(batch)
            batch_id += 1

        for row in self._deleted_rows:
            batch = SP.Method(SP.Field(unicode(row.id),
                                       Name='ID'),
                              ID=unicode(batch_id), Cmd='Delete')
            rows_by_batch_id[batch_id] = row
            batches.append(batch)
            batch_id += 1

        response = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                         soapaction='http://schemas.microsoft.com/sharepoint/soap/UpdateListItems')

        for result in response.xpath('.//sp:Result', namespaces=namespaces):
            batch_id, batch_result = result.attrib['ID'].split(',')
            row = rows_by_batch_id[int(batch_id)]
            if batch_result in ('Update', 'New'):
                row._update(result.xpath('z:row', namespaces=namespaces)[0],
                            clear=True)
            else:
                self._deleted_rows.remove(row)

        assert not self._deleted_rows
        assert [(not row._changed) for row in self.rows]

class SharePointListRow(object):
    # fields, list and opener are added as class attributes in SharePointList.row_class

    def __init__(self, row={}):
        self._update(row, clear=True)

    def _update(self, row, clear=False):
        if clear:
            self._data = {}
            self._changed = set()
        for field in self.fields:
            value = field.parse(row)
            if value is not None:
                self._data[field.name] = value
        try:
            self.id = self.ID
        except AttributeError:
            self.id = None

    def __repr__(self):
        return "<SharePointListRow {0} '{1}'>".format(self.id, self.name)

    def delete(self):
        self.list.remove(self)

    @property
    def name(self):
        try:
            return self.Title
        except AttributeError:
            return self.LinkFilename

    def get_batch_method(self):
        """
        Returns a change batch for SharePoint's UpdateListItems operation.
        """
        if not self._changed:
            return None

        batch_method = E.Method(Cmd='Update' if self.id else 'New')
        batch_method.append(E.Field(unicode(self.id) if self.id else 'New',
                                    Name='ID'))
        for field in self.fields:
            if field.name in self._changed:
                value = field.unparse(self._data[field.name] or '')
                batch_method.append(E.Field(value, Name=field.name))
        return batch_method

    @property
    def is_file(self):
        return hasattr(self, 'LinkFilename')

    def as_xml(self, transclude_xml=False, **kwargs):
        fields_element = OUT('fields')
        row_element = OUT('row', fields_element, id=unicode(self.id))
        for field in self.fields:
            try:
                data = self._data[field.name]
            except KeyError:
                pass
            else:
                fields_element.append(field.as_xml(self, data, **kwargs))
        if transclude_xml and self.is_file and self._data.get('DocIcon') == 'xml':
            try:
                content = etree.parse(self.open()).getroot()
            except urllib2.HTTPError, e:
                content_element = OUT('content', missing='true')
            else:
                content_element = OUT('content', content)
            row_element.append(content_element)
        return row_element

    def open(self):
        url = self.opener.relative(self.list.meta['Title'] + '/' + urllib.quote(self.LinkFilename))
        request = urllib2.Request(url)
        request.add_header('Translate', 'f')
        return self.opener.open(request)
