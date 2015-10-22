import json
import os
from unittest.mock import MagicMock
from urllib.parse import urljoin

import requests
import falcon
import pytest

from data_acquisition.consts import ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH
from data_acquisition.resources import AcquisitionRequestsResource
from .consts import TEST_DOWNLOAD_REQUEST
from .utils import dict_is_part_of, simulate_falcon_request


class MockApi(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_queue = MagicMock()
        self.mock_req_store = MagicMock()
        self.fake_downloader_url = urljoin('http://fake-downloader-url', DOWNLOADER_PATH)


@pytest.fixture(scope='module')
def falcon_api():
    api = MockApi()
    api.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(
            req_store=api.mock_req_store,
            queue=api.mock_queue,
            downloader_url=api.fake_downloader_url)
    )
    return api


def test_post_acquisition_request(falcon_api):
    test_port = 12345
    os.environ['VCAP_APP_PORT'] = str(test_port)
    fake_token = 'bearer some+base64+bytes'

    resp_body, headers = simulate_falcon_request(
        api=falcon_api,
        path=ACQUISITION_PATH,
        encoding='utf-8',
        method='POST',
        body=json.dumps(TEST_DOWNLOAD_REQUEST),
        headers=[('Authorization', fake_token)]
    )
    resp_json = json.loads(resp_body)

    assert headers.status == falcon.HTTP_202
    assert dict_is_part_of(resp_json, TEST_DOWNLOAD_REQUEST)

    proper_downloader_req = {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': 'http://localhost:{}{}'.format(test_port, DOWNLOAD_CALLBACK_PATH)
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        requests.post,
        url=falcon_api.fake_downloader_url,
        json=proper_downloader_req,
        headers={'Authorization': fake_token}
    )

    req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], resp_json['id'])
    falcon_api.mock_req_store.set.assert_called_with(req_store_id, resp_body)
    assert resp_json['status'] == 'VALIDATED'


def test_post_acquisition_request_bad_request(falcon_api):
    broken_request = dict(TEST_DOWNLOAD_REQUEST)
    del broken_request['category']

    _, headers = simulate_falcon_request(
        api=falcon_api,
        path=ACQUISITION_PATH,
        encoding='utf-8',
        method='POST',
        body=json.dumps(broken_request),
    )
    assert headers.status == falcon.HTTP_400

# TODO test callback from metadata parser
# TODO test getting one entry for an org
# TODO test deleting an entry
# TODO test getting all entries for an org
# TODO test getting all entries as an admin