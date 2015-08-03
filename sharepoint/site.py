import functools
try:
    from urllib.request import Request
    from urllib.parse import urljoin
except ImportError:
    from urllib2 import Request
    from urlparse import urljoin

from lxml import etree

from .lists import SharePointLists
from .users import SharePointUsers
from .xml import soap_body, namespaces, OUT

class SharePointSite(object):
    def __init__(self, url, opener, timeout=None):
        if not url.endswith('/'):
            url += '/'

        self.opener = opener
        self.opener.base_url = url
        self.opener.post_soap = self.post_soap
        self.opener.relative = functools.partial(urljoin, url)
        self.timeout = timeout

    def post_soap(self, url, xml, soapaction=None):
        url = self.opener.relative(url)
        request = Request(url, etree.tostring(soap_body(xml)))
        request.add_header('Content-type', 'text/xml; charset=utf-8')
        if soapaction:
            request.add_header('Soapaction', soapaction)
        response = self.opener.open(request, timeout=self.timeout)
        return etree.parse(response).xpath('/soap:Envelope/soap:Body/*', namespaces=namespaces)[0]

    @property
    def lists(self):
        if not hasattr(self, '_lists'):
            self._lists = SharePointLists(self.opener)
        return self._lists

    @property
    def users(self):
        if not hasattr(self, '_users'):
            self._users = SharePointUsers(self.opener)
        return self._users

    def as_xml(self, include_lists=False, include_users=False, **kwargs):
        xml = OUT.site(url=self.opener.base_url)
        if include_lists or kwargs.get('list_names'):
            xml.append(self.lists.as_xml(**kwargs))
        if include_users:
            if 'user_ids' not in kwargs:
                kwargs['user_ids'] = set(xml.xpath('.//sharepoint:user/@id', namespaces=namespaces))
            xml.append(self.users.as_xml(**kwargs))
        return xml
            
