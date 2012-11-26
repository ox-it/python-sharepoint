import base64
import urllib2

class PreemptiveBasicAuthHandler(urllib2.BaseHandler):

    def __init__(self, password_manager):
        self.password_manager = password_manager

    def http_request(self, request):
        url = request.get_full_url()
        username, password = self.password_manager.find_user_password(None,url)
        if password is None:
            return request

        raw = "%s:%s" % (username, password)
        auth = 'Basic %s' % base64.b64encode(raw).strip()

        request.add_unredirected_header('Authorization', auth)
        return request
    https_request = http_request


def basic_auth_opener(url, username, password):
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, username, password)
    auth_handler = PreemptiveBasicAuthHandler(password_manager)
    opener = urllib2.build_opener(auth_handler)
    return opener
