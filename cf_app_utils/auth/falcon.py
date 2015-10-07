__author__ = 'butla'

import jwt
import requests


class JwtMiddleware:

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

    def process_request(self, req, resp):
        pass

    def process_resource(self, req, resp, resource):
        # TODO check if the resource isn't exempted from security checking
        token = req.auth.split()[1] # skip 'bearer'
        payload = jwt.decode(token, key=self._verification_key)

    def process_response(self, req, resp, resource):
        pass
