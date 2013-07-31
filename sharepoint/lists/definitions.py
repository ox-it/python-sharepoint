"""
Common definitions for dealing with SharePoint lists.
"""

# Relative to the base URL for the SharePoint site
LIST_WEBSERVICE = '_vti_bin/Lists.asmx'

# From http://msdn.microsoft.com/en-us/library/lists.lists.addlist%28v=office.12%29.aspx
LIST_TEMPLATES = {
    'Announcements': 104,
    'Contacts': 105,
    'Custom List': 100,
    'Custom List in Datasheet View': 120,
    'DataSources': 110,
    'Discussion Board': 108,
    'Document Library': 101,
    'Events': 106,
    'Form Library': 115,
    'Issues': 1100,
    'Links': 103,
    'Picture Library': 109,
    'Survey': 102,
    'Tasks': 107
}

