from .site import SharePointSite, basic_auth_opener

def main():
    from optparse import OptionParser
    import os
    import sys
    from lxml import etree

    parser = OptionParser()
    parser.add_option('-s', '--site-url', dest='site_url', help='Root URL for the SharePoint site')
    parser.add_option('-l', '--list-name', dest='list_name', help='Name of the list to retrieve')
    parser.add_option('-u', '--username', dest='username', help='Username')
    parser.add_option('-p', '--password', dest='password', help='Password')
    parser.add_option('-c', '--credentials', dest='credentials', help="File containing 'username:password'.")

    options, args = parser.parse_args()

    if not options.site_url:
        sys.stderr.write("--site-url is a required parameter. Use -h for more information.\n")
        sys.exit(1)

    if options.credentials:
        username, password = open(os.path.expanduser(options.credentials)).read().strip().split(':', 1)    
    elif not (options.username and options.password):
        sys.stderr.write("--credentials, or --username and --password must be supplied. Use -h for more information.\n")
        sys.exit(1)
    else:
        username, password = options.username, options.password

    opener = basic_auth_opener(options.site_url, username, password)
    site = SharePointSite(options.site_url, opener)

    if options.list_name:
        try:
            sharepoint_list = site.lists[options.list_name]
        except KeyError:
            sys.stderr.write("No list with name '%s'.\n" % options.list_name)
            sys.exit(1)

        sys.stdout.write(etree.tostring(sharepoint_list.as_xml(), pretty_print=True))
    else:
        for sharepoint_list in site.lists:
            print sharepoint_list.name

if __name__ == '__main__':
    main()

