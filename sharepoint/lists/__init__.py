import collections
import re
try:
    from urllib.parse import quote
    from urllib.request import HTTPError, Request
except ImportError:
    from urllib import quote
    from urllib2 import HTTPError, Request

from lxml import etree
from lxml.builder import E

from sharepoint.xml import SP, namespaces, OUT
from sharepoint.lists import moderation
from sharepoint.lists.types import type_mapping, default_type, UserField, LookupField
from sharepoint.lists.attachments import SharePointAttachments
from sharepoint.lists.definitions import LIST_WEBSERVICE, LIST_TEMPLATES
from sharepoint.exceptions import UpdateFailedError

uuid_re = re.compile(r'^\{?([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})\}?$')

try:
    str = basestring
except NameError:
    pass


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
                self._all_lists.append(SharePointList(self.opener, self, list_element))
            
            # Explicitly request information about the UserInfo list.
            # This can be accessed with the name "User Information List"
            result = self.opener.post_soap(LIST_WEBSERVICE, SP.GetList(SP.listName("UserInfo")))
            list_element = result.xpath('.//sp:List', namespaces=namespaces)[0]
            self._all_lists.append(SharePointList(self.opener, self, list_element))

        return self._all_lists

    def remove(self, list):
        """
        Removes a list from the site.
        """
        xml = SP.DeleteList(SP.listName(list.id))
        result = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                       soapaction='http://schemas.microsoft.com/sharepoint/soap/DeleteList')
        self.all_lists.remove(list)

    def create(self, name, description='', template=100):
        """
        Creates a new list in the site.
        """
        try:
            template = int(template)
        except ValueError:
            template = LIST_TEMPLATES[template]
        if name in self:
            raise ValueError("List already exists: '{0}".format(name))
        if uuid_re.match(name):
            raise ValueError("Cannot create a list with a UUID as a name")
        xml = SP.AddList(SP.listName(name),
                         SP.description(description),
                         SP.templateID(unicode(template)))
        result = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                       soapaction='http://schemas.microsoft.com/sharepoint/soap/AddList')
        list_element = result.xpath('sp:AddListResult/sp:List', namespaces=namespaces)[0]
        self._all_lists.append(SharePointList(self.opener, self, list_element))

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
        elif isinstance(key, str):
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

    def as_xml(self, list_names=None, **kwargs):
        if list_names is not None:
            lists = (self[list_name] for list_name in list_names)
        else:
            lists = self
        return OUT.lists(*[l.as_xml(**kwargs) for l in lists])

class SharePointList(object):
    def __init__(self, opener, lists, settings):
        self.opener = opener
        self.lists = lists
        self._deleted_rows = set()
        self._settings, self._meta = settings, None
        self.id = self.meta['ID'].lower()

    def __repr__(self):
        return "<SharePointList {0} '{1}'>".format(self.id, self.meta['Title'])

    @property
    def name(self):
        return self.meta['Title']

    @property
    def meta(self):
        if not self._meta:
            settings = self._settings if self._settings is not None else self.settings
            self._meta = dict(settings.attrib)
        return self._meta

    @property
    def settings(self):
        if self._settings is None or not len(self._settings):
            xml = SP.GetList(SP.listName(self.id))
            response = self.opener.post_soap(LIST_WEBSERVICE, xml)
            self._settings = response[0][0]
        return self._settings
    
    @property
    def moderation(self):
        if self._meta['EnableModeration'] != 'True':
            raise AttributeError('Moderation not enabled on this list')
        elif not hasattr(self, '_moderation'):
            self._moderation = moderation.Moderation(self)
        return self._moderation

    def get_rows(self, folder=''):
        rows = []
        attribs = collections.defaultdict(dict)
        field_groups, lookup_count = [[]], 0
        for field in self.fields.values():
            if isinstance(field, (UserField, LookupField)):
                lookup_count += 1
            if lookup_count >= 8:
                lookup_count = 0
                field_groups.append([])
            field_groups[-1].append(field)
        for field_group in field_groups:
            # Request all fields, not just the ones in the default view
            view_fields = E.ViewFields(*(E.FieldRef(Name=field.name) for field in field_group))
            #query_options = E.QueryOptions(E.ViewAttributes(Scope="Recursive"))
            query_options = E.QueryOptions(E.Folder(folder))
            xml = SP.GetListItems(SP.listName(self.id),
                                  SP.rowLimit("100000"),
                                  SP.viewFields(view_fields),
                                  SP.queryOptions(query_options))
            response = self.opener.post_soap(LIST_WEBSERVICE, xml)
            for row in list(response[0][0][0]):
                attrib = attribs[row.attrib['ows_ID']]
                attrib.update(row.attrib)
        for attrib in attribs.values():
            rows.append(self.Row(attrib=attrib))
        return list(rows)

    @property
    def rows(self):
        if not hasattr(self, '_rows'):
            self._rows = self.get_rows()
        return list(self._rows)

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
            self._fields = {}
            for field in self.settings.xpath('sp:Fields/sp:Field', namespaces=namespaces):
                field_class = type_mapping.get(field.attrib['Type'], default_type)
                field = field_class(self.lists, self.id, field)
                self._fields[field.name] = field
        return self._fields

    @property
    def Row(self):
        """
        The class for a row in this list.
        """
        if not hasattr(self, '_row_class'):
            attrs = {'fields': self.fields, 'list': self, 'opener': self.opener}
            for field in self.fields.values():
                attrs[field.name] = field.descriptor
            self._row_class = type('SharePointListRow', (SharePointListRow,), attrs)
        return self._row_class

    def as_xml(self, include_list_data=True, include_field_definitions=True, **kwargs):
        list_element = OUT('list', name=self.name, id=self.id)

        if include_field_definitions:
            fields_element = OUT('fields')
            for field in self.fields.values():
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

        if include_list_data:
            rows_element = OUT('rows')
            for row in self.rows:
                rows_element.append(row.as_xml(**kwargs))
            list_element.append(rows_element)
        return list_element

    def append(self, row):
        """
        Appends a row to the list. Takes a dictionary, returns a row.
        """
        if isinstance(row, dict):
            row = self.Row(row)
        elif isinstance(row, self.Row):
            pass
        elif isinstance(row, SharePointListRow):
            raise TypeError("row must be a dict or an instance of SharePointList.Row, not SharePointListRow")
        else:
            raise TypeError("row must be a dict or an instance of SharePointList.Row")
        self.rows # Make sure self._rows exists.
        self._rows.append(row)
        return row
    
    def append_from(self, other_list):
        for row in other_list.rows:
            self.append(row.as_row(self.Row))

    def remove(self, row):
        """
        Removes the row from the list.
        """
        self._rows.remove(row)
        self._deleted_rows.add(row)

    def delete(self):
        """
        Deletes the list from the site.
        """
        self.lists.remove(self)

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
        batches = E.Batch(ListVersion='1', OnError='Return')
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
            batch = E.Method(E.Field(unicode(row.id),
                                     Name='ID'),
                             ID=unicode(batch_id), Cmd='Delete')
            rows_by_batch_id[batch_id] = row
            batches.append(batch)
            batch_id += 1

        if len(batches) == 0:
            return

        response = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                         soapaction='http://schemas.microsoft.com/sharepoint/soap/UpdateListItems')

        for result in response.xpath('.//sp:Result', namespaces=namespaces):
            batch_id, batch_result = result.attrib['ID'].split(',')
            row = rows_by_batch_id[int(batch_id)]

            error_code = result.find('sp:ErrorCode', namespaces=namespaces)
            error_text = result.find('sp:ErrorText', namespaces=namespaces)
            if error_code is not None and error_code.text != '0x00000000':
                raise UpdateFailedError(row, batch_result,
                                        error_code.text,
                                        error_text.text)

            if batch_result in ('Update', 'New'):
                row._update(result.xpath('z:row', namespaces=namespaces)[0],
                            clear=True)
            else:
                self._deleted_rows.remove(row)

        assert not self._deleted_rows
        assert not any(row._changed for row in self.rows)

class SharePointListRow(object):
    # fields, list and opener are added as class attributes in SharePointList.Row

    def __init__(self, row=None, attrib=None):
        self._update(row, attrib, clear=True)

    def _update(self, row, attrib=None, clear=False):
        if clear:
            self._data = {}
            self._changed = set()
        if isinstance(row, etree._Element):
            attrib = row.attrib
        if attrib:
            for field in self.fields.values():
                value = field.parse(attrib)
                if value is not None:
                    self._data[field.name] = value
        elif isinstance(row, dict):
            for key in row:
                setattr(self, key, row[key])
        elif row is not None:
            raise TypeError("row should be a dict or etree._Element.")
        try:
            self.id = self.ID
        except AttributeError:
            self.id = None

    def __repr__(self):
        return "<SharePointListRow {0} {1}>".format(self.id, repr(self.name))

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
        for field in self.fields.values():
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
        for field in self.fields.values():
            try:
                data = self._data[field.name]
            except KeyError:
                pass
            else:
                fields_element.append(field.as_xml(self, data, **kwargs))
        if transclude_xml and self.is_file and self._data.get('DocIcon') == 'xml':
            try:
                content = etree.parse(self.open()).getroot()
            except HTTPError as e:
                content_element = OUT('content', missing='true')
            else:
                content_element = OUT('content', content)
            row_element.append(content_element)
        return row_element

    def as_dict(self, with_immutable=True, field_names=None):
        data = {}
        for field in self.fields.values():
            if not with_immutable and field.immutable:
                continue
            if field_names is not None and field.name not in field_names:
                continue
            data[field.name] = getattr(self, field.name)
        return data

    def as_row(self, list_or_row):
        row = list_or_row.Row if isinstance(list_or_row, SharePointList) else list_or_row
        field_names = set(row.fields) & set(self.fields)
        field_names -= set(['Attachments', '_Level', 'File_x0020_Type', '_CopySource', '_UIVersionString', 'FileLeafRef', 'Edit', 'LinkFilenameNoMenu', '_EditMenuTableEnd', '_ModerationComments', 'owshiddenversion', 'ContentType', 'ContentTypeId', '_HasCopyDestinations', 'EncodedAbsUrl', 'LinkTitle', 'WorkflowVersion', 'BaseName'])
        field_names -= set(f for f in field_names if f.startswith('_'))
        return row(self.as_dict(with_immutable=False, field_names=field_names))

    def open(self):
        url = self.opener.relative(quote(self.list.meta['Title']) + '/' + quote(self.LinkFilename.encode('utf-8')))
        request = Request(url)
        request.add_header('Translate', 'f')
        return self.opener.open(request)

    @property
    def attachments(self):
        if not hasattr(self, '_attachments'):
            self._attachments = SharePointAttachments(self.opener, self.list.id, self.id)
        return self._attachments
