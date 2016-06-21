"""
Utility functions used by the tests.
"""

import json

from falcon.testing import StartResponseMock, create_environ
from requests.structures import CaseInsensitiveDict

from tests.consts import TEST_AUTH_HEADER


def dict_is_part_of(dict_a, dict_b):
    """
    Checks whether dict_b is a part of dict_a.
    That is if dict_b is dict_a, just with some keys removed.
    :param dict dict_a:
    :param dict dict_b:
    :rtype: bool
    """
    dict_a, dict_b = CaseInsensitiveDict(dict_a), CaseInsensitiveDict(dict_b)
    for key, value in dict_b.items():
        if key not in dict_a or dict_a[key] != value:
            return False
    return True


class FalconApiTestClient:
    """Can be conveniently used to simulate requests to a `falcon.API`.

    Args:
        api (falcon.API): API object to send the request to.
    """

    def __init__(self, api):
        self._api = api

    def get(self, path, query_string=''):
        resp_body, headers = simulate_falcon_request(
            api=self._api,
            path=path,
            query_string=query_string,
            encoding='utf-8',
            method='GET',
            headers=[('Authorization', TEST_AUTH_HEADER)]
        )
        resp_json = json.loads(resp_body) if resp_body else None
        return resp_json, headers

    def post(self, path, data):
        resp_body, headers = simulate_falcon_request(
            api=self._api,
            path=path,
            body=json.dumps(data),
            encoding='utf-8',
            method='POST',
            headers=[('Authorization', TEST_AUTH_HEADER)]
        )
        resp_json = json.loads(resp_body) if resp_body else None
        return resp_json, headers

    def delete(self, path):
        _, headers = simulate_falcon_request(
            api=self._api,
            path=path,
            encoding='utf-8',
            method='DELETE',
            headers=[('Authorization', TEST_AUTH_HEADER)])
        return headers


def simulate_falcon_request(api, path='/', encoding=None, **kwargs):
    """Simulates a request to a `falcon.API`.

    Args:
        api (falcon.API): API object to send the request to.
        path (str, optional): The path to request.
        encoding (str, optional): If this is set to a character encoding,
            such as 'utf-8', `simulate_falcon_request` will assume the
            response is a single byte string, and will decode it as the
            result of the request, rather than simply returning the
            standard WSGI iterable.
        kwargs (optional): Same as those defined for
            `falcon.testing.create_environ`.

    """
    resp_headers = StartResponseMock()
    result = api(
        create_environ(path=path, **kwargs),
        resp_headers)

    final_result = result

    if encoding is not None:
        if result:
            final_result = result[0].decode(encoding)
        else:
            final_result = ''

    return final_result, resp_headers
