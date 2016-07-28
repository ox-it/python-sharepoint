import base64

try:
    from urllib.request import BaseHandler, HTTPPasswordMgrWithDefaultRealm, build_opener
except ImportError:
    from urllib2 import BaseHandler, HTTPPasswordMgrWithDefaultRealm, build_opener

from ntlm import HTTPNtlmAuthHandler

class PreemptiveBasicAuthHandler(BaseHandler):

    def __init__(self, password_manager):
        self.password_manager = password_manager

    def http_request(self, request):
        url = request.get_full_url()
        username, password = self.password_manager.find_user_password(None,url)
        if password is None:
            return request

        raw = "%s:%s" % (username, password)
        auth = 'Basic %s' % base64.b64encode(raw.encode('utf-8')).decode('utf-8').strip()

        request.add_unredirected_header('Authorization', auth)
        return request
    https_request = http_request


def basic_auth_opener(url, username, password):
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, username, password)
    auth_handler = PreemptiveBasicAuthHandler(password_manager)
    opener = build_opener(auth_handler)
    return opener

def ntlm_auth_opener(url, user, password):
	password_manager = HTTPPasswordMgrWithDefaultRealm()
	password_manager.add_password(None, url, user, password)
	auth_NTLM = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(password_manager)
	return build_opener(auth_NTLM)
