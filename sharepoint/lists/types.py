import datetime
import itertools
import warnings

from ..xml import OUT
from ..users import SharePointUser
from ..utils import decode_entities
from . import moderation

empty_values = ('', None)

if bytes == str: # Py2
    str = unicode

class FieldDescriptor(object):
    def __init__(self, field, immutable=False):
        self.field = field
        self.immutable = immutable
    def __get__(self, instance, owner):
        try:
            return self.field.descriptor_get(instance, instance._data[self.field.name])
        except KeyError:
            return None

    def __set__(self, instance, value):
        if self.immutable:
            raise AttributeError("Field '{0}' is immutable".format(self.field.name))

        new_value = self.field.descriptor_set(instance, value)
        if not self.field.is_equal(new_value, instance._data.get(self.field.name)):
            instance._data[self.field.name] = new_value
            instance._changed.add(self.field.name)

class MultiFieldDescriptor(FieldDescriptor):
    def __get__(self, instance, owner):
        values = instance._data.get(self.field.name, ())
        return [self.field.descriptor_get(instance, value) for value in values]

    def __set__(self, instance, values):
        new_value = [self.field.descriptor_set(instance, value) for value in values]
        if not self.field.is_equal(new_value, instance._data.get(self.field.name)):
            instance._data[self.field.name] = new_value
            instance._changed.add(self.field.name)

class Field(object):
    group_multi = None
    multi = None
    type_name = 'unknown'
    immutable = False
    default_value = None

    def __init__(self, lists, list_id, xml):
        self.lists, self.list_id = lists, list_id
        self.name = xml.attrib['Name']
        self.display_name = xml.attrib['DisplayName']
        self.description = xml.attrib.get('Description')
        self.sharepoint_type = xml.attrib['Type']
        if self.multi is None:
            self.multi = xml.attrib.get('Mult') == 'TRUE'

    def parse(self, attrib):
        value = attrib.get('ows_' + self.name)
        if value in empty_values:
            return self.default_value

        if self.multi:
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
                values = [values[i:i+self.group_multi] for i in range(0, len(values), self.group_multi)]

                # if we have [['']], then remove the last entry
                if values and values[-1] and not values[-1][0]:
                    del values[-1]
                return map(self._parse, values)
            else:
                return [self._parse(v) for v in values if v not in empty_values]
        elif self.group_multi:
            values = value.split(';#', self.group_multi-1)
            return self._parse(values)
        else:
            return self._parse(value)

    def unparse(self, value):
        if value in empty_values:
            return ''

        if self.group_multi is not None and self.multi:
            value = map(self._unparse, value)
            assert all(len(v) == self.group_multi for v in value)
            value = list(itertools.chain(*value))
        elif self.group_multi is not None:
            value = self._unparse(value)
            assert len(value) == self.group_multi
        elif self.multi:
            value = map(self._unparse, value)

        if self.group_multi is not None or self.multi:
            values = [subvalue.replace(';', ';;') for subvalue in value]
            if self.group_multi is not None:
                return ';#'.join(values)
            else:
                # It expects ';#foo;#bar;#baz;#'
                if not values:
                    return ''
                return ';#'.join([''] + values + [''])
        else:
            return self._unparse(value)

    def _parse(self, value):
        raise NotImplementedError
    def _unparse(self, value):
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

    def is_equal(self, new, original):
        return new == original

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
    default_value = ''
    maximum_length = None

    def __init__(self, lists, list_id, xml):
        if xml.attrib.get('MaxLength'):
            self.maximum_length = int(xml.attrib['MaxLength'])
        self.rich_text = xml.attrib.get('RichText') == 'TRUE'
        return super(TextField, self).__init__(lists, list_id, xml)

    def descriptor_get(self, row, value):
        return value or ''

    def descriptor_set(self, row, value):
        if self.maximum_length and len(value or '') > self.maximum_length:
            raise ValueError('Value is too long ({0}, instead of {1} characters)'.format(len(value or ''), self.maximum_length))
        return value or ''

    def is_equal(self, new, original):
        if self.rich_text and \
           isinstance(new, str) and \
           isinstance(original, str):
            return decode_entities(new) == decode_entities(original)
        return new == original

    def _parse(self, value):
        return value or ''
    def _unparse(self, value):
        return value or ''

class LookupField(Field):
    group_multi = 2
    type_name = 'lookup'

    def __init__(self, lists, list_id, xml):
        super(LookupField, self).__init__(lists, list_id, xml)
        self.lookup_list = xml.attrib['List']

    def _parse(self, value):
        return {'list': self.lookup_list, 'id': int(value[0]), 'title': value[1]}
    def _unparse(self, value):
        return [unicode(value['id']), value['title'] or '']

    def descriptor_get(self, row, value):
        return row.list.lists[value['list']].rows_by_id[value['id']]
    def descriptor_set(self, row, value):
        from . import SharePointListRow # lets avoid a circular import
        if isinstance(value, SharePointListRow):
            return {'list': self.lookup_list, 'id': value.ID, 'title': row.name}
        elif isinstance(value, int):
            return {'list': self.lookup_list, 'id': value, 'title': None}
        elif isinstance(value, dict):
            value = value.copy()
            value['list'] = self.lookup_list
            assert 'id' in value and 'title' in value
            assert isinstance(value['id'], int)
        elif isinstance(value, (list, tuple)):
            assert len(value) == 2
            return {'list': self.lookup_list, 'id': int(value[0]), 'title': value[1]}
        else:
            assert TypeError("value must be a row, a row ID, a dict, or a two-element iterable")

    def _as_xml(self, row, value, follow_lookups=False, **kwargs):
        value_element = OUT('lookup', list=value['list'], id=unicode(value['id']))
        if follow_lookups:
            value_element.append(self.descriptor_get(row, value).as_xml())
        return value_element

    def extra_field_definition(self):
        return {'list': self.lookup_list}

class URLField(Field):
    type_name = 'url'

    def _parse(self, value):
        href, text = value.split(', ', 1)
        return {'href': href, 'text': text}
    def _unparse(self, value):
        if value is None:
            return ''
        else:
            return '{href}, {text}'.format(**value)

    def descriptor_set(self, row, value):
        if not value:
            value = None
            return None
        elif isinstance(value, str):
            value = {'href': value, 'text': ''}
        elif isinstance(value, tuple) and len(value) == 2:
            value = {'href': value[0], 'text': value[1]}
        elif isinstance(value, dict):
            assert 'href' in value
            if 'text' not in value:
                value['text'] = ''
        else:
            raise AttributeError("Value must be a str, href-text pair, or dict, not a {0}.".format(value))
        if not any(value['href'].startswith(prefix) for prefix in ('mailto:', 'http:', 'https:')):
            raise ValueError("'{0}' is not a valid URL".format(value['href']))
        return value

    def _as_xml(self, row, value, **kwargs):
        return OUT('url', value['text'], href=value['href'])


class ChoiceField(Field):
    type_name = 'choice'

    def _parse(self, value):
        return value
    def _unparse(self, value):
        return value

class MultiChoiceField(ChoiceField):
    multi = True

    def parse(self, xml):
        values = super(MultiChoiceField, self).parse(xml)
        if values is not None:
            return [value for value in values if value]

class DateTimeField(Field):
    type_name = 'dateTime'

    def _parse(self, value):
        return datetime.datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    def _unparse(self, value):
        return value.isoformat(' ')

    def _as_xml(self, row, value, **kwargs):
        return OUT('dateTime', value.isoformat())

class UnknownField(Field):
    def _parse(self, value):
        return value
    def _unparse(self, value):
        return value

    def _as_xml(self, row, value, **kwargs):
        return OUT('unknown', unicode(value))

class CounterField(Field):
    type_name = 'counter'
    immutable = True

    def _parse(self, value):
        return int(value)

    def _as_xml(self, row, value, **kwargs):
        return OUT('int', unicode(value))

class NumberField(Field):
    type_name = 'number'

    def _parse(self, value):
        return float(value)
    def _unparse(self, value):
        return unicode(value)

    def descriptor_set(self, row, value):
        if value is None:
            return None
        return float(value)

    def _as_xml(self, row, value, **kwargs):
        return OUT('number', unicode(value))

class IntegerField(NumberField):
    type_name = 'integer'
    def _parse(self, value):
        return int(value)
    def descriptor_set(self, row, value):
        if value is None:
            return None
        return int(value)
    def _as_xml(self, row, value, **kwargs):
        return OUT('int', unicode(value))

class BooleanField(Field):
    type_name = 'boolean'
    def _parse(self, value):
        return value == '1'
    def _unparse(self, value):
        return '1' if value else '0'
    def descriptor_set(self, row, value):
        return bool(value)
    def _as_xml(self, row, value, **kwargs):
        return OUT('boolean', 'true' if value else 'false')

class UserField(Field):
    group_multi = 2
    type_name = 'user'

    def _parse(self, value):
        assert isinstance(value, (list, tuple))
        assert len(value) == 2
        return {'id': int(value[0]), 'name': value[1]}
    def _unparse(self, value):
        return [unicode(value['id']), value.get('name', '')]
    
    def descriptor_set(self, row, value):
        if value is None:
            return None
        if isinstance(value, int):
            return {'id': value}
        elif isinstance(value, dict):
            return value
        elif isinstance(value, SharePointUser):
            return {'id': value.id, 'name': value.Name}
        else:
            raise AttributeError("UserField must be set to an int or dict.")

    def _as_xml(self, row, value, **kwargs):
        return OUT('user', value['name'], id=unicode(value['id']))

class UserMultiField(UserField):
    multi = True

class CalculatedField(Field):
    group_multi = 2
    immutable = True
    
    types = {'float': float}
    type_names = {float: 'float',
                  str: 'text',
                  int: 'int'}
    def _parse(self, value):
        type_name, value = value
        try:
            return self.types[type_name](value)
        except KeyError:
            warnings.warn("Unknown calculated type '%s'" % type_name)
            return value

    def _as_xml(self, row, value, **kwargs):
        element_name = self.type_names.get(type(value), 'unknown')
        return getattr(OUT, element_name)(unicode(value), calculated='true')

class ModerationStatusField(Field):
    group_multi = 2
    immutable = True
    
    def _parse(self, value):
        return moderation.moderation_statuses[int(value[0])]
    def _unparse(self, value):
        return [unicode(value.value), value.label.title()]

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
                'UserMulti': UserMultiField,
                'Calculated': CalculatedField,
                'Number': NumberField,
                'Integer': IntegerField,
                'Boolean': BooleanField,
                'ModStat': ModerationStatusField}
default_type = UnknownField
