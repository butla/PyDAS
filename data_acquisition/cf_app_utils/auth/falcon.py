"""
Authorization/authentication components for Falcon apps.
"""

import logging

import jwt
import falcon

from . import get_uaa_key, UserOrgAccessChecker, NoOrgAccessError, PermissionServiceError


class JwtMiddleware:

    """
    JWT middleware for Falcon.
    """

    # TODO should be more complex, see https://tools.ietf.org/html/rfc6750#section-3
    AUTH_CHALLENGE = 'Bearer'

    def __init__(self):
        self._verification_key = None
        self._log = logging.getLogger(type(self).__name__)

    def initialize(self, uaa_key_url):
        """
        Prepares the middleware object for work. Needs to be called before any requests to the app.
        Actually downloads the public key that will be used to verify JWT signature.
        :param str uaa_key_url: URL under which the public key to verify a token can be found.
        :raises `UaaError`: when getting the key fails
        """
        self._verification_key = get_uaa_key(uaa_key_url)

    def process_request(self, req, resp):
        """
        Doesn't do anything. Part of Falcon middleware interface.
        """
        pass

    def process_resource(self, req, resp, resource, params): #pylint: disable=unused-argument
        """
        Verifies the JWT token used when calling the resource.
        Some resources may have disabled this verification, when they should be publicly accessible.
        """
        # TODO check if the resource isn't exempted from security checking
        if not req.auth or not req.auth.startswith('bearer '):
            err_msg = 'Authorization header missing or not containing "bearer" prefix.'
            self._log.error(err_msg)
            raise falcon.HTTPUnauthorized('Bad Authorization header', err_msg, self.AUTH_CHALLENGE)

        token = req.auth.split()[1] # skip 'bearer'
        try:
            jwt.decode(token, key=self._verification_key, options={'verify_aud': False})
        except Exception as ex:
            err_msg = 'Verification of the JWT token has failed.'
            self._log.exception(err_msg)
            raise falcon.HTTPUnauthorized('Invalid token', err_msg, self.AUTH_CHALLENGE) from ex

    def process_response(self, req, resp, resource):
        """
        Doesn't do anything. Part of Falcon middleware interface.
        """
        pass


class FalconUserOrgAccessChecker(UserOrgAccessChecker):

    """
    Wrapper for `UserOrgAccessChecker` that throws Falcon errors.
    Should be used from within Falcon resources.
    """

    def validate_access(self, user_token, org_ids):
        try:
            super().validate_access(user_token, org_ids)
        except NoOrgAccessError as ex:
            raise falcon.HTTPForbidden(
                "User doesn't have access to resource.",
                "User doesn't have sufficient rights in organization owning the resource."
            ) from ex
        except PermissionServiceError as ex:
            raise falcon.HTTPServiceUnavailable(
                'Error when contacting permission service.',
                "The User Management service couldn't be contacted or experienced errors.",
                10
            ) from ex
