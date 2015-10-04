__author__ = 'butla'

import jwt
import requests

from talons.auth.interfaces import Identifies, Identity
from talons.auth.external import Authenticator
from talons.auth.external import Authorizer


class JwtIdentifier(Identifies):

    def __init__(self, uaa_key_url):
        """
        :param str uaa_key_url: URL under which the public key to verify a token can be found.
        """
        self._key_url = uaa_key_url
        self._verification_key = None

    def initialize(self):
        response = requests.get(self._key_url)
        if not response.status_code == 200:
            raise Exception('freakout, no public key')
        print(response.text)
        print(response.json())
        self._verification_key = response.json()['value']

    def identify(self, request):
        token = request.auth.split()[1] # skip 'bearer'
        payload = jwt.decode(token, key=self._verification_key)

        request.env[self.IDENTITY_ENV_KEY] = Identity('someone')
        print('identified')
        # TODO if admin is in scope, add admin to roles
        return True


def get_identifier(verification_key_url):
    return JwtIdentifier(verification_key_url)


def get_authorizer():
    return Authorizer(external_authz_callable=_authorize)


def get_authenticator():
    return Authenticator(external_authn_callable=_authenticate)


def _authenticate(identity):
    print('authenticating')
    return True


def _authorize(identity, request_action):
    print('authorizing')
    return True
