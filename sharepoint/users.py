import urllib2

from lxml import etree

from .xml import namespaces, OUT

USER_PATH = '_vti_bin/ListData.svc/UserInformationList({0})'

class SharePointUsers(object):
    def __init__(self, opener):
        self.opener = opener
        self._users = {}
    
    def __getitem__(self, key):
        if key not in self._users:
            url = self.opener.base_url + USER_PATH.format(key)
            try:
                data = self.opener.open(url)
            except urllib2.HTTPError, e:
                if e.code == 404:
                    self._users[key] = None
                else:
                    raise
            else:
                props = etree.parse(data).xpath('.//m:properties/*',
                                                namespaces=namespaces)
                self._users[key] = SharePointUser(key, props)
        if self._users[key] is None:
            raise KeyError
        return self._users[key]

class SharePointUser(object):
    def __init__(self, id, props):
        self._props = props
        self._data = {}
        self.id = id
        prefix = '{' + namespaces['d'] + '}'
        for prop in props:
            tag = prop.tag
            ns, local = tag[1:].split('}', 1)
            name = tag.split('}', 1)[-1]
            if prop.attrib.get('{{{0}}}null'.format(namespaces['m'])) == 'true':
                value = None
            else:
                value = prop.text
            self._data[(ns, local)] = value
            if not tag.startswith(prefix):
                continue
            setattr(self, name, value)

    def __getitem__(self, key):
        return self._data[key]

    def __repr__(self):
        return "<SharePointUser '{0}'>".format(self.Name)

    def __unicode__(self):
        return self.Name

    def as_xml(self, **kwargs):
        return OUT.user(*self._props, id=unicode(self.id))