import base64
from ntlm3 import HTTPNtlmAuthHandler

from six.moves.urllib.request import BaseHandler, HTTPPasswordMgrWithDefaultRealm, build_opener


class PreemptiveBasicAuthHandler(BaseHandler):

    def __init__(self, password_manager):
        self.password_manager = password_manager

    def http_request(self, request):
        url = request.get_full_url()
        username, password = self.password_manager.find_user_password(None, url)
        if password is None:
            return request

        raw = "%s:%s" % (username, password)
        auth = 'Basic %s' % base64.b64encode(raw.encode('utf-8')).decode('utf-8').strip()

        request.add_unredirected_header('Authorization', auth)
        return request
    https_request = http_request


def auth_opener(url, username, password, ntlm=False):
    password_manager = HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, url, username, password)
    if ntlm:
        auth_handler = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(password_manager)
    else:
        auth_handler = PreemptiveBasicAuthHandler(password_manager)
    opener = build_opener(auth_handler)
    return opener

# including for backwards compatability
def basic_auth_opener(url, username, password):
    return auth_opener(url, username, password, ntlm=False)
    
def ntlm_auth_opener(url, username, password):
    return auth_opener(url, username, password, ntlm=True)