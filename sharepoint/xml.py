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
    'z': '#RowsetSchema', # Yes, really.
}

SOAP = builder.ElementMaker(namespace=namespaces['soap'], nsmap=namespaces)
T = builder.ElementMaker(namespace=namespaces['t'], nsmap=namespaces)
SP = builder.ElementMaker(namespace=namespaces['sp'], nsmap=namespaces)
SPD = builder.ElementMaker(namespace=namespaces['spd'], nsmap=namespaces)
UPS = builder.ElementMaker(namespace=namespaces['ups'], nsmap=namespaces)

def soap_body(*args, **kwargs):
    return SOAP.Envelope(SOAP.Body(*args, **kwargs))
