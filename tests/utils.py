"""
Utility functions and classes used by the tests.
"""

import json
from urllib.parse import urlencode

import bravado_core.response
import bravado.http_future
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
    Passes a proper authorization token with each request to get through the authorization
    mechanisms.

    Args:
        api (`falcon.API`): API object to send the request to.
    """

    def __init__(self, api):
        self._api = api

    # TODO to make this universal, the TEST_AUTH_HEADER needs to be factored out
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
        api (`falcon.API`): API object to send the request to.
        path (str, optional): The path to request.
        encoding (str, optional): If this is set to a character encoding,
            such as 'utf-8', `simulate_falcon_request` will assume the
            response is a single byte string, and will decode it as the
            result of the request, rather than simply returning the
            standard WSGI iterable.
        kwargs (optional): Same as those defined for
            `falcon.testing.helpers.create_environ`.

    Returns:
        A tuple containing responses body and an object with additional response information, like
            headers, status code, etc.
    """
    response_info = StartResponseMock()
    result = api(
        create_environ(path=path, **kwargs),
        response_info)

    final_result = result

    if encoding is not None:
        if result:
            final_result = result[0].decode(encoding)
        else:
            final_result = ''

    return final_result, response_info

# TODO move to separate file (bravado_integrations)
# TODO separate falcon_integrations file

# TODO redo the description and maybe inherit the original client
class FalconTestHttpClient(object):
    """Interface for a minimal HTTP client that can retrieve Swagger specs
    and perform HTTP calls to fulfill a Swagger operation.

    Args:
        api (`falcon.API`): API object to send the requests to.
    """

    def __init__(self, falcon_api):
        self._api = falcon_api

    def request(self, request_params, operation=None, response_callbacks=None,
                also_return_response=False):
        """
        :param request_params: complete request data. e.g. url, method,
            headers, body, params, connect_timeout, timeout, etc.
        :type request_params: dict
        :param operation: operation that this http request is for. Defaults
            to None - in which case, we're obviously just retrieving a Swagger
            Spec.
        :type operation: :class:`bravado_core.operation.Operation`
        :param response_callbacks: List of callables to post-process the
            incoming response. Expects args incoming_response and operation.
        :param also_return_response: Consult the constructor documentation for
            :class:`bravado.http_future.HttpFuture`.

        :returns: HTTP Future object
        :rtype: :class: `bravado_core.http_future.HttpFuture`
        """
        falcon_test_future = FalconTestFutureAdapter(request_params, self._api)

        return bravado.http_future.HttpFuture(
            falcon_test_future,
            FalconTestResponseAdapter,
            operation,
            response_callbacks,
            also_return_response)


class FalconTestFutureAdapter:
    """Mimics a :class:`concurrent.futures.Future` for the purposes of making it work with
    Bravado's :class:`bravado.http_future.HttpFuture` when simulating calls to a Falcon API.
    Those calls will be validated by Bravado.

    Args:
        request_params (dict): Request parameters provided to
            :class:`bravado.http_client.HttpClient` interface.
        falcon_api (`falcon.API`): API object to send the request to.
        response_encoding (str): Encoding that will be used to decode response's body.
            If set to None then the body won't be decoded.
    """

    def __init__(self, request_params, falcon_api, response_encoding='utf-8'):
        self._falcon_api = falcon_api
        self._request_params = request_params
        self._response_encoding = response_encoding


    def result(self, **_):
        """
        Args:
            **_: Ignore all the keyword arguments (right now it's just timeout) passed by Bravado.
        """
        # Bravado will create the URL by appending request path to 'http://localhost'
        path = self._request_params['url'].replace('http://localhost', '')
        query_string = urlencode(self._request_params.get('params', {}))
        return simulate_falcon_request(api=self._falcon_api,
                                       path=path,
                                       encoding=self._response_encoding,
                                       query_string=query_string,
                                       headers=self._request_params.get('headers'),
                                       body=self._request_params.get('data'),
                                       method=self._request_params.get('method'))


class FalconTestResponseAdapter(bravado_core.response.IncomingResponse):
    """Wraps a response from `simulate_falcon_request` to provide a uniform interface
    expected by Bravado's :class:`bravado.http_future.HttpFuture`.
    It's used when simulating calls to a Falcon API.
    Those calls will be validated by Bravado.

    Args:
        falcon_test_response: A tuple returned from `simulate_falcon_request`.
    """

    def __init__(self, falcon_test_response):
        self._response_body = falcon_test_response[0]
        self._response_info = falcon_test_response[1]

    @property
    def status_code(self):
        # status codes from Falcon look like this: "200 OK"
        return int(self._response_info.status[:3])

    @property
    def text(self):
        return self._response_body

    @property
    def reason(self):
        # status codes from Falcon look like this: "200 OK"
        return self._response_info.status[4:]

    @property
    def headers(self):
        return self._response_info.headers

    def json(self, **kwargs):
        return json.loads(self._response_body,**kwargs)
