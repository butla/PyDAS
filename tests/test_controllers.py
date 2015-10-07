import json
import requests

import falcon
from falcon.testing.helpers import create_environ
from falcon.testing.srmock import StartResponseMock

import pytest
from unittest.mock import MagicMock

from data_acquisition.app import SampleResource


class MockApi(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_queue = MagicMock()
        self.fake_downloader_url = 'http://fake-downloader-url'


@pytest.fixture(scope='module')
def falcon_api():
    api = MockApi()
    api.add_route('/', SampleResource(api.mock_queue, api.fake_downloader_url))
    return api


def simulate_falcon_request(api, path='/', encoding=None, **kwargs):
    """Simulates a request to a `falcon.API`.

    Args:
        path (str): The path to request.
        decode (str, optional): If this is set to a character encoding,
            such as 'utf-8', `simulate_request` will assume the
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


def test_hello_endpoint(falcon_api):
    resp_body, headers = simulate_falcon_request(api=falcon_api, path='/', encoding='utf-8')
    assert resp_body == 'Hello world\n'
    assert headers.status == falcon.HTTP_200


def test_post_endpoint(falcon_api):
    fake_token = 'bearer some+base64+bytes'

    resp_body, headers = simulate_falcon_request(
        api=falcon_api,
        path='/',
        encoding='utf-8',
        method='POST',
        body=json.dumps({'something': 'nothing'}),
        headers=[
            ('Content-type', 'application/json'),
            ('Authorization', fake_token)]
    )

    assert not resp_body
    assert headers.status == falcon.HTTP_200
    falcon_api.mock_queue.enqueue.assert_called_with(
        requests.post,
        url=falcon_api.fake_downloader_url,
        json={'something': 'yeah, not much'},
        headers={'Authorization': fake_token}
    )