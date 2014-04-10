try:
    from urllib.request import HTTPError
    from urllib.parse import urlparse, parse_qs
except ImportError:
    from urllib2 import HTTPError
    from urlparse import urlparse, parse_qs

from lxml import etree
from lxml.builder import E

from .xml import namespaces, OUT, SP, SEARCH, SQ

USER_PATH = '_vti_bin/ListData.svc/UserInformationList({0})'

PEOPLE_WEBSERVICE = '_vti_bin/People.asmx'
SEARCH_WEBSERVICE = '_vti_bin/search.asmx'


class SharePointUsers(object):
    def __init__(self, opener):
        self.opener = opener
        self._users = {}
        self._user_searches = {}
        self._resolved_principals = {}
    
    def __getitem__(self, key):
        key = int(key)
        if key not in self._users:
            url = self.opener.base_url + USER_PATH.format(key)
            try:
                data = self.opener.open(url)
            except HTTPError as e:
                if e.code == 404:
                    self._users[key] = None
                else:
                    raise
            else:
                props = etree.parse(data).xpath('.//m:properties/*',
                                                namespaces=namespaces)
                self._users[key] = SharePointUser(key, props)
        if self._users[key] is None:
            raise KeyError(key)
        return self._users[key]

    def resolve_principal(self, principal):
        return self.resolve_principals([principal])[0]

    def resolve_principals(self, principals):
        principals_to_resolve = set(p for p in principals if p not in self._resolved_principals)

        if principals_to_resolve:
            xml = SP.ResolvePrincipals(SP.principalKeys(*(SP.string(p) for p in principals_to_resolve)))
            xml.append(SP.principalType('All'))
            result = self.opener.post_soap(PEOPLE_WEBSERVICE, xml)

            for principal_info in result.xpath('*/sp:PrincipalInfo', namespaces=namespaces):
                user_id = int(principal_info.find('sp:UserInfoID', namespaces=namespaces).text)
                account_name = principal_info.find('sp:AccountName', namespaces=namespaces).text
                display_name = principal_info.find('sp:DisplayName', namespaces=namespaces)
                display_name = display_name.text if display_name is not None else ''
                if user_id == -1:
                    raise ValueError("User {0} ({1}) not yet in SharePoint.".format(account_name,
                                                                                    display_name))
                self._resolved_principals[account_name] = self[user_id]

        return [self._resolved_principals.get(p) for p in principals]

    def search(self, name, max_results=None):
        if name in self._user_searches:
            return self._user_searches[name]
        query = SQ.QueryPacket(
            E.Query(
                E.Context(
                    E.QueryText(
                        'SCOPE:"People"' + name
                    ,type='STRING'),
                )
            ),
        )
        xml = SEARCH.Query(SEARCH.queryXml(etree.tostring(query)))
        results = self.opener.post_soap(SEARCH_WEBSERVICE, xml, soapaction='urn:Microsoft.Search/Query')
        results = etree.fromstring(results.find('search:QueryResult', namespaces=namespaces).text)
        account_names = []
        for result in results.xpath('.//srd:Document', namespaces=namespaces):
            link = result.xpath('srd:Action/srd:LinkUrl', namespaces=namespaces)[0].text
            account_name = parse_qs(urlparse(link).query)['accountname'][0]
            account_names.append(account_name)

        users = self.resolve_principals(account_names)
        self._user_searches[name] = users
        return users


    def as_xml(self, user_ids, **kwargs):
        xml = OUT.users()
        for user_id in user_ids:
            xml.append(self[user_id].as_xml())
        return xml

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
