"""
Functions dedicated to making sure that a user has access
to the organisation's resources he/she requests.
"""

import json
import logging
from urllib.parse import urljoin

from jwt.utils import base64url_decode
import requests

USER_MANAGEMENT_PATH = '/rest/orgs/permissions'


class UserOrgAccessChecker:

    """
    Checks if a user has access to organization's data.
    """

    def __init__(self, checker_url):
        """
        :param checker_url: URL of the service that can check user's permissions.
        """
        self._log = logging.getLogger(type(self).__name__)
        self._checker_url = checker_url

    def validate_access(self, user_token, org_ids):
        """
        Validates that the user actually has access to the given organizations.
        If the user doesn't have access an error is raised.
        Access mean either being in that organization or having the role of console.admin.

        WARNING: This method can only be used AFTER the token was verified.

        :param str user_token: User's OAuth 2 token payload (containing "bearer" prefix).
        :param list[str] org_ids: IDs of organizations that the user needs to have access to
        :rtype: None
        :raises `PermissionServiceError`: When getting user's org permissions fails.
        :raises `NoOrgAccessError`: When user doesn't have access to all of the specified orgs.
        """
        if self._user_is_admin(user_token):
            return
        self._check_user_org_access(user_token, org_ids)

    @staticmethod
    def _user_is_admin(user_token):
        """
        :param str user_token: User's OAuth 2 token payload (containing "bearer" prefix).
        :return: True if the user is an admin.
        :rtype: bool
        """
        # get token without "bearer"
        token = user_token.split()[1]
        # take the middle part with payload
        token_payload_based = token.split('.')[1]
        token_payload_str = base64url_decode(token_payload_based.encode()).decode()
        token_payload = json.loads(token_payload_str)
        return 'console.admin' in token_payload['scope']

    def _check_user_org_access(self, user_token, org_ids):
        """
        Calls the user management service to see if the user has access to the given organizations.
        :param str user_token: User's OAuth 2 token payload (containing "bearer" prefix).
        :param list[str] org_ids: IDs of organizations that the user needs to have access to
        :rtype: None
        :raises `PermissionServiceError`: When getting user's org permissions fails.
        :raises `NoOrgAccessError`: When user doesn't have access to all of the specified orgs.
        """
        resp = requests.get(
            urljoin(self._checker_url, USER_MANAGEMENT_PATH),
            headers={'Authorization': user_token})
        if resp.status_code != 200:
            self._log.error(
                "Failed to get user's organizations from service "
                "at %s\nStatus code: %s\nResponse: %s",
                self._checker_url,
                resp.status_code,
                resp.text)
            raise PermissionServiceError()

        user_orgs = set([entry['organization']['metadata']['guid'] for entry in resp.json()])
        requested_orgs = set(org_ids)

        if not user_orgs.issuperset(requested_orgs):
            msg = "User doesn't have access to the given organizations: {}".format(
                requested_orgs - user_orgs)
            self._log.error(msg)
            raise NoOrgAccessError(msg)


class NoOrgAccessError(Exception):
    """
    User doesn't have access to the requested resource.
    """
    pass


class PermissionServiceError(Exception):
    """
    Signals that there either was a problem connecting to the service that decides if a user has
    access to an organization, or that the service had errors.
    """
    pass
