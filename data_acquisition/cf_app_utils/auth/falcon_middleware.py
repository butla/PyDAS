"""
JWT middleware for Falcon.
"""

import jwt
import logging
import requests

import falcon


class JwtMiddleware:

    """
    JWT middleware for Falcon.
    """

    def __init__(self, verification_key_url):
        """
        :param str verification_key_url: URL under which the public key to verify a token can be found.
        """
        self._key_url = verification_key_url
        self._verification_key = None
        self._log = logging.getLogger(type(self).__name__)

    def initialize(self):
        """
        Prepares the middleware object for work. Needs to be called before any requests to the app.
        Actually downloads the public key that will be used to verify JWT signature.
        :raises Exception: when bad things happen TODO
        """
        response = requests.get(self._key_url)
        # TODO sensible exceptions
        if not response.status_code == 200:
            # TODO add logging
            raise Exception('Freakout, no public key. Message: {}'.format(response.text))
        self._verification_key = response.json()['value']

    def process_request(self, req, resp):
        """
        Doesn't do anything. Part of Falcon middleware interface.
        """
        pass

    def process_resource(self, req, resp, resource):
        """
        Verifies the JWT token used when calling the resource.
        Some resources may have disabled this verification, when they should be publicly accessible.
        """
        # TODO check if the resource isn't exempted from security checking
        if not req.auth or not req.auth.startswith('bearer '):
            err_msg = 'Authorization header missing or not containing "bearer" prefix.'
            self._log.error(err_msg)
            raise falcon.HTTPUnauthorized('Bad Authorization header', err_msg)

        token = req.auth.split()[1] # skip 'bearer'
        try:
            jwt.decode(token, key=self._verification_key)
        except Exception:
            err_msg = 'Verification of the JWT token has failed.'
            self._log.exception(err_msg)
            raise falcon.HTTPUnauthorized('Invalid token', err_msg)

    def process_response(self, req, resp, resource):
        """
        Doesn't do anything. Part of Falcon middleware interface.
        """
        pass
