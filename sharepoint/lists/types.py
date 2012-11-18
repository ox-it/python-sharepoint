import datetime
import warnings

from ..xml import OUT

class FieldDescriptor(object):
    def __init__(self, field, immutable=False):
        self.field = field
        self.immutable = immutable
    def __get__(self, instance, owner):
        try:
            return self.field.descriptor_get(instance, instance._data[self.field.name])
        except KeyError:
            raise AttributeError

    def __set__(self, instance, value):
        if self.immutable:
            raise AttributeError("Field '{0}' is immutable".format(self.field.name))
        instance._data[self.field.name] = self.field.descriptor_set(instance, value)
        instance._changed.add(self.field.name)

class MultiFieldDescriptor(object):
    def __init__(self, field):
        self.field = field
    def __get__(self, instance, owner):
        try:
            values = instance.data[self.field.name]
            return [self.field.descriptor_get(instance, value) for value in values]
        except KeyError:
            raise AttributeError

class Field(object):
    group_multi = None
    multi = None
    type_name = 'unknown'
    immutable = False

    def __init__(self, lists, list_id, xml):
        self.lists, self.list_id = lists, list_id
        self.name = xml.attrib['Name']
        self.display_name = xml.attrib['DisplayName']
        self.description = xml.attrib.get('Description')
        self.sharepoint_type = xml.attrib['Type']
        if self.multi is None:
            self.multi = xml.attrib.get('Mult') == 'TRUE'

    def get(self, row):
        value = row.attrib.get('ows_' + self.name)
        if value is None:
            return None

        values, start, pos = [], 0, -1
        while True:
            pos = value.find(';', pos+1)
            if pos == -1:
                values.append(value[start:].replace(';;', ';'))
                break
            elif value[pos:pos+2] == ';;':
                pos += 2
                continue
            elif value[pos:pos+2] == ';#':
                values.append(value[start:pos].replace(';;', ';'))
                start = pos = pos + 2
            else:
                pos += 2
                warnings.warn("Upexpected character after ';': {0}".format(value[pos+1]))
                #raise ValueError("Unexpected character after ';': {0}".format(value[pos+1]))
                continue

        if self.group_multi is not None:
            values = [values[i:i+self.group_multi] for i in xrange(0, len(values), self.group_multi)]

        if self.multi:
            # if we have [['']], then remove the last entry
            if values and not values[-1][0]:
                del values[-1]
            return map(self.parse, values)
        else:
            return self.parse(values[0])

    def parse(self, value):
        raise NotImplementedError

    @property
    def descriptor(self):
        if not hasattr(self, '_descriptor'):
            descriptor_class = (MultiFieldDescriptor if self.multi else self.descriptor_class)
            self._descriptor = descriptor_class(self, self.immutable)
        return self._descriptor
    descriptor_class = FieldDescriptor

    def descriptor_get(self, row, value):
        return value

    def descriptor_set(self, row, value):
        return value

    def as_xml(self, row, value, **kwargs):
        field_element = OUT('field', name=self.name)
        if self.multi:
            for subvalue in value:
                field_element.append(self._as_xml(row, subvalue, **kwargs))
        else:
            field_element.append(self._as_xml(row, value, **kwargs))
        return field_element
    
    def _as_xml(self, row, value, **kwargs):
        return OUT('text', unicode(value))
    
    def __repr__(self):
        return u"<%s '%s'>" % (type(self).__name__, self.name)

    def extra_field_definition(self):
        return {}

class TextField(Field):
    type_name = 'text'

    def parse(self, value):
        return value

class LookupFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, owner):
        lookup_list, row_id = instance.data[self.name]
        return instance.list.lists[lookup_list].rows_by_id[row_id]

class LookupField(Field):
    group_multi = 2
    type_name = 'lookup'

    def __init__(self, lists, list_id, xml):
        super(LookupField, self).__init__(lists, list_id, xml)
        self.lookup_list = xml.attrib['List']

    def parse(self, value):
        return {'list': self.lookup_list, 'id': int(value[0])}

    def descriptor_get(self, row, value):
        return row.list.lists[value['list']].rows_by_id[value['id']]

    def _as_xml(self, row, value, follow_lookups=False, **kwargs):
        value_element = OUT('lookup', list=value['list'], id=unicode(value['id']))
        if follow_lookups:
            value_element.append(self.descriptor_get(row, value).as_xml())
        return value_element

    def extra_field_definition(self):
        return {'list': self.lookup_list}

class URLField(Field):
    type_name = 'url'

    def parse(self, value):
        href, text = value.split(', ', 1)
        return {'href': href, 'text': text}

    def _as_xml(self, row, value, **kwargs):
        return OUT('url', value['text'], href=value['href'])


class ChoiceField(Field):
    type_name = 'choice'

    def parse(self, value):
        return value

class MultiChoiceField(ChoiceField):
    multi = True

    def get(self, xml):
        values = super(MultiChoiceField, self).get(xml)
        if values is not None:
            return [value for value in values if value]

class DateTimeField(Field):
    type_name = 'dateTime'

    def parse(self, value):
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')

    def _as_xml(self, row, value, **kwargs):
        return OUT('dateTime', value.isoformat())

class UnknownField(Field):
    def parse(self, value):
        return value

    def _as_xml(self, row, value, **kwargs):
        return OUT('unknown', unicode(value))

class CounterField(Field):
    type_name = 'counter'
    immutable = True

    def parse(self, value):
        return int(value)

    def _as_xml(self, row, value, **kwargs):
        return OUT('int', unicode(value))

class UserField(Field):
    group_multi = 2
    type_name = 'user'

    def parse(self, value):
        return {'id': value[0], 'name': value[1]}

    def _as_xml(self, row, value, **kwargs):
        return OUT('user', value['name'], id=unicode(value['id']))

class UserMultiField(UserField):
    multi = True

type_mapping = {'Text': TextField,
                'Lookup': LookupField,
                'LookupMulti': LookupField,
                'URL': URLField,
                'Choice': ChoiceField,
                'MultiChoice': MultiChoiceField,
                'DateTime': DateTimeField,
                'Counter': CounterField,
                'Computed': TextField,
                'Note': TextField,
                'User': UserField,
                'UserMulti': UserMultiField}
default_type = UnknownField
