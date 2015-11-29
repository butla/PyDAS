from unittest.mock import MagicMock

import falcon
from falcon import Request
from falcon import Response
from falcon.testing.helpers import create_environ
import pytest
import responses

from .consts import RSA_2048_PUB_KEY, TEST_AUTH_HEADER, TEST_ADMIN_AUTH_HEADER, TEST_ORG_UUID
from data_acquisition.cf_app_utils.auth.falcon_middleware import JwtMiddleware
from data_acquisition.cf_app_utils.auth import *


def test_oauth_middleware_init_ok(monkeypatch):
    fake_key_url = 'http://fake-url'
    fake_uaa_resp = MagicMock()
    fake_uaa_resp.status_code = 200
    fake_uaa_resp.json.return_value = {'value': RSA_2048_PUB_KEY}

    mock_requests = MagicMock()
    mock_requests.get.return_value = fake_uaa_resp
    monkeypatch.setattr(
        'data_acquisition.cf_app_utils.auth.falcon_middleware.requests',
        mock_requests)

    auth_middleware = JwtMiddleware(fake_key_url)

    auth_middleware.initialize()

    mock_requests.get.assert_called_with(fake_key_url)


def test_oauth_middleware_init_fail(monkeypatch):
    # TODO remove code repetition. Parameterized fixture? Or a function?
    fake_key_url = 'http://fake-url'
    fake_uaa_resp = MagicMock()
    fake_uaa_resp.status_code = 404
    fake_uaa_resp.json.return_value = {'value': RSA_2048_PUB_KEY}

    mock_requests = MagicMock()
    mock_requests.get.return_value = fake_uaa_resp
    monkeypatch.setattr(
        'data_acquisition.cf_app_utils.auth.falcon_middleware.requests',
        mock_requests)

    auth_middleware = JwtMiddleware(fake_key_url)

    with pytest.raises(Exception):
        auth_middleware.initialize()


def test_oauth_middleware_request_auth_valid():
    auth_middleware = JwtMiddleware('http://fake-url')
    auth_middleware._verification_key = RSA_2048_PUB_KEY
    test_req = Request(create_environ(headers={'Authorization': TEST_AUTH_HEADER}))
    test_resp = Response()

    auth_middleware.process_resource(test_req, test_resp, None)
    auth_middleware.process_request(test_req, test_resp)
    auth_middleware.process_response(test_req, test_resp, None)


@pytest.mark.parametrize('headers', [
    {},
    {'Authorization': ''},
    {'Authorization': '{}Z{}'.format(TEST_AUTH_HEADER[:-2], TEST_AUTH_HEADER[-1])},
])
def test_oauth_middleware_request_auth_invalid(headers):
    auth_middleware = JwtMiddleware('http://fake-url')
    auth_middleware._verification_key = RSA_2048_PUB_KEY

    with pytest.raises(falcon.HTTPUnauthorized):
        auth_middleware.process_resource(
            Request(create_environ(headers=headers)),
            None,
            None)


FAKE_PERMISSION_SERVICE_URL = 'http://fake-address'
FAKE_PERMISSION_URL = FAKE_PERMISSION_SERVICE_URL + USER_MANAGEMENT_PATH

@pytest.fixture(scope='function')
def user_org_access_checker():
    return UserOrgAccessChecker(FAKE_PERMISSION_SERVICE_URL, RSA_2048_PUB_KEY)


def _set_positive_permission_service_mock():
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=200, json=[
        {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
    ])


@responses.activate
def test_user_in_org_with_access(user_org_access_checker):
    _set_positive_permission_service_mock()
    user_org_access_checker.validate_access(TEST_AUTH_HEADER, [TEST_ORG_UUID])


@responses.activate
def test_user_in_org_without_access(user_org_access_checker):
    _set_positive_permission_service_mock()
    with pytest.raises(NoOrgAccessError):
        user_org_access_checker.validate_access(TEST_AUTH_HEADER, ['not-the-users-org'])


def test_admin_user_in_org(user_org_access_checker):
    user_org_access_checker.validate_access(
        TEST_ADMIN_AUTH_HEADER,
        [TEST_ORG_UUID, 'some-other-org'])


@responses.activate
def test_user_in_org_no_service(user_org_access_checker):
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=404)
    with pytest.raises(PermissionServiceError):
        user_org_access_checker.validate_access(TEST_AUTH_HEADER, [TEST_ORG_UUID])
