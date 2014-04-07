from lxml.builder import E
from lxml import etree

from sharepoint.xml import SP, namespaces

LIST_WEBSERVICE = '_vti_bin/Lists.asmx'

class ModerationStatus(object):
    def __init__(self, value, label):
        self.value, self.label = value, label
    def __repr__(self):
        return self.label
    def __unicode__(self):
        return self.label

APPROVED = ModerationStatus(0, 'approved')
REJECTED = ModerationStatus(1, 'rejected')
PENDING = ModerationStatus(2, 'pending')
DRAFT = ModerationStatus(3, 'draft')
SCHEDULED = ModerationStatus(4, 'scheduled')

moderation_statuses = {0: APPROVED,
                       1: REJECTED,
                       2: PENDING,
                       3: DRAFT,
                       4: SCHEDULED}

def _moderation_status_filter(status):
    def status_filter(self):
        return (r for r in self._list.rows if r._ModerationStatus == status)
    status_filter.__name__ = status.label
    return property(status_filter)

class Moderation(object):
    def __init__(self, list):
        self._list = list
    
    approved = _moderation_status_filter(APPROVED)
    rejected = _moderation_status_filter(REJECTED)
    pending = _moderation_status_filter(PENDING)
    draft = _moderation_status_filter(DRAFT)
    scheduled = _moderation_status_filter(SCHEDULED)

    def rows_by_status(self, status):
        return (r for r in self._list.rows if r._ModerationStatus == status)

    def set_status(self, rows, status, comment=None):
        rows_by_batch_id, batch_id = {}, 1
        
        if isinstance(status, int):
            status = moderation_statuses[status]
        
        batches = E.Batch(ListVersion='1', OnError='Return')
        # Here's the root element of our SOAP request.
        xml = SP.UpdateListItems(SP.listName(self._list.id), SP.updates(batches))

        if comment:
            comment = E.Field(unicode(comment),
                              Name='_ModerationComment')
        
        for row in rows:
            batch = E.Method(E.Field(unicode(row.id),
                                     Name='ID'),
                             E.Field(unicode(status.value),
                                     Name='_ModerationStatus'),
                             ID=unicode(batch_id), Cmd='Moderate')
            if comment:
                batch.append(comment)
            rows_by_batch_id[batch_id] = row
            batches.append(batch)
            batch_id += 1

        response = self._list.opener.post_soap(LIST_WEBSERVICE, xml,
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

            if batch_result == 'Moderate':
                row._update(result.xpath('z:row', namespaces=namespaces)[0],
                            clear=True)
