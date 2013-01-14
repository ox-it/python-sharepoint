from lxml import builder

namespaces = {
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'wsdl': 'http://schemas.xmlsoap.org/wsdl/',
    'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
    't': 'http://schemas.microsoft.com/exchange/services/2006/types',
    'sp': 'http://schemas.microsoft.com/sharepoint/soap/',
    'spd': 'http://schemas.microsoft.com/sharepoint/soap/directory/',
    'rs': 'urn:schemas-microsoft-com:rowset',
    'ups': 'http://microsoft.com/webservices/SharePointPortalServer/UserProfileService/GetUserProfileByIndex',
    'd': 'http://schemas.microsoft.com/ado/2007/08/dataservices',
    'm': 'http://schemas.microsoft.com/ado/2007/08/dataservices/metadata',
    'search': 'urn:Microsoft.Search',
    'sq': 'urn:Microsoft.Search.Query',
    'sr': 'urn:Microsoft.Search.Response',
    'srd': 'urn:Microsoft.Search.Response.Document',
    'z': '#RowsetSchema', # Yes, really.
    'sharepoint': 'https://github.com/ox-it/python-sharepoint/', # Ours
}

SOAP = builder.ElementMaker(namespace=namespaces['soap'], nsmap=namespaces)
T = builder.ElementMaker(namespace=namespaces['t'], nsmap=namespaces)
SP = builder.ElementMaker(namespace=namespaces['sp'], nsmap=namespaces)
SPD = builder.ElementMaker(namespace=namespaces['spd'], nsmap=namespaces)
UPS = builder.ElementMaker(namespace=namespaces['ups'], nsmap=namespaces)
SQ = builder.ElementMaker(namespace=namespaces['sq'], nsmap=namespaces)

OUT = builder.ElementMaker(namespace=namespaces['sharepoint'], nsmap=namespaces)

SEARCH = builder.ElementMaker(namespace=namespaces['search'], nsmap={None: namespaces['search']})
SQ = builder.ElementMaker(namespace=namespaces['sq'], nsmap={None: namespaces['sq']})

def soap_body(*args, **kwargs):
    return SOAP.Envelope(SOAP.Body(*args, **kwargs))
