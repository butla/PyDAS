"""
Classes necessary for doing Falcon unit tests through Bravado.
"""
import json
from urllib.parse import urlencode

import bravado.http_future
import bravado_core.response

from tests.falcon_testing import simulate_falcon_request

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
