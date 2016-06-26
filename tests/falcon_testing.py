import json
from falcon.testing import StartResponseMock, create_environ
from tests.consts import TEST_AUTH_HEADER


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