from .site import SharePointSite, basic_auth_opener

def main():
    from optparse import OptionParser, OptionGroup
    import os
    import sys
    import warnings
    from lxml import etree

    warnings.simplefilter("ignore")

    description = ["A utility to extract data from SharePoint sites, returning ",
                   "XML. Available actions are 'lists' (returns a list of ",
                   "lists in the SharePoint site), and 'exportlists' (returns ",
                   "data for all or specified lists"]

    parser = OptionParser(usage='%prog action [options]',
                          description=''.join(description))
    parser.add_option('-s', '--site-url', dest='site_url', help='Root URL for the SharePoint site')
    parser.add_option('-u', '--username', dest='username', help='Username')
    parser.add_option('-p', '--password', dest='password', help='Password')
    parser.add_option('-c', '--credentials', dest='credentials', help="File containing 'username:password'.")

    parser.add_option('-n', '--pretty-print', dest='pretty_print', action='store_true', default=True)
    parser.add_option('-N', '--no-pretty-print', dest='pretty_print', action='store_false')

    list_options = OptionGroup(parser, 'List options')
    list_options.add_option('-l', '--list-name', dest='list_names', help='Name of a list to retrieve. Can be repeated to return multiple lists. If not present at all, all lists will be returned.', action='append')
    list_options.add_option('-d', '--data', dest='include_data', action='store_true', default=True, help="Include list data in output (default for export_lists)")
    list_options.add_option('-D', '--no-data', dest='include_data', action='store_false', help="Don't include list data in output")
    list_options.add_option('-f', '--fields', dest='include_field_definitions', action='store_true', default=True, help="Include field definitions data in output (default for export_lists)")
    list_options.add_option('-F', '--no-fields', dest='include_field_definitions', action='store_false', help="Don't include field definitions data in output")
    list_options.add_option('-t', '--transclude-xml', dest='transclude_xml', action='store_true', default=False, help="Transclude linked XML files into row data")
    list_options.add_option('-T', '--no-transclude-xml', dest='transclude_xml', action='store_false', help="Don't transclude XML")
    parser.add_option_group(list_options)

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

    if not len(args) == 1:
        sys.stderr.write("You must provide an action. Use -h for more information.\n")
        sys.exit(1)

    action = args[0]

    if action == 'lists':
        xml = site.lists.as_xml(options.list_names or None,
                                include_data=False,
                                include_field_definitions=False)
    elif action == 'exportlists':
        xml = site.lists.as_xml(options.list_names or None,
                                include_data=options.include_data,
                                include_field_definitions=options.include_field_definitions,
                                transclude_xml=options.transclude_xml)
    else:
        sys.stderr.write("Unsupported action: '%s'. Use -h to discover supported actions.\n")
        sys.exit(1)

    sys.stdout.write(etree.tostring(xml, pretty_print=options.pretty_print))

if __name__ == '__main__':
    main()

