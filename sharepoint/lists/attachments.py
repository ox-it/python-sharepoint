from sharepoint.xml import namespaces, SP
from sharepoint.lists.definitions import LIST_WEBSERVICE

class SharePointAttachments(object):
    def __init__(self, opener, list_id, row_id):
        self.opener = opener
        self.list_id, self.row_id = list_id, row_id

    def __iter__(self):
        """
        Returns an iterator over attachments for a list item.

        Implements http://msdn.microsoft.com/en-us/library/websvclists.lists.getattachmentcollection.aspx
        """
        xml = SP.GetAttachmentCollection(SP.listName(self.list_id),
                                         SP.listItemID(str(self.row_id)))
        response = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                         soapaction='http://schemas.microsoft.com/sharepoint/soap/GetAttachmentCollection')
        for url in response.xpath('//sp:Attachment', namespaces=namespaces):
            yield SharePointAttachment(self, url.text)

    def delete(self, url):
        xml = SP.DeleteAttachment(SP.listName(self.list_id), SP.listItemID(str(self.row_id)), SP.url(url))
        response = self.opener.post_soap(LIST_WEBSERVICE, xml, 
                                         soapaction='http://schemas.microsoft.com/sharepoint/soap/DeleteAttachment')

    def add(self, filename, content):
        xml = SP.AddAttachment(SP.listName(self.list_id), SP.listItemID(str(self.row_id)), SP.fileName(filename), SP.attachment(content))
        response = self.opener.post_soap(LIST_WEBSERVICE, xml,
                                         soapaction='http://schemas.microsoft.com/sharepoint/soap/AddAttachment')

    def open(self, url):
        return self.opener.open(url)

class SharePointAttachment(object):
    def __init__(self, attachments, url):
        self.attachments, self.url = attachments, url

    def delete(self):
        self.attachments.delete(self.url)

    def open(self):
        return self.attachments.open(self.url)

    def __unicode__(self):
        return self.url

    def __repr__(self):
        return "<{0} '{1}'>".format(type(self).__name__, self.url)

