import json
import os
from unittest.mock import MagicMock
from urllib.parse import urljoin

import requests
import falcon
import pytest

from data_acquisition import DasConfig
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_PATH, USER_MANAGEMENT_PATH)
from data_acquisition.resources import AcquisitionRequestsResource
from .consts import TEST_DOWNLOAD_REQUEST
from .utils import dict_is_part_of, simulate_falcon_request


class MockApi(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_queue = MagicMock()
        self.mock_req_store = MagicMock()


@pytest.fixture(scope='module')
def das_config():
    return DasConfig(
        self_url='https://my-fake-url',
        port=12345,
        redis_host='redis.example.com',
        redis_port=54321,
        redis_password='secret-password',
        downloader_url=urljoin('https://fake-downloader-url', DOWNLOADER_PATH),
        metadata_parser_url=urljoin('https://fake-metadata-url', METADATA_PARSER_PATH),
        user_management_url=urljoin('https://fake-userman-url', USER_MANAGEMENT_PATH),
        verification_key_url='http://fake-verification-key-url'
    )


@pytest.fixture(scope='module')
def falcon_api(das_config):
    api = MockApi()
    api.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(
            req_store=api.mock_req_store,
            queue=api.mock_queue,
            config=das_config)
    )
    return api


def test_acquisition_request(falcon_api, das_config):
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
        'callback': 'https://my-fake-url' + DOWNLOAD_CALLBACK_PATH
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        requests.post,
        url=das_config.downloader_url,
        json=proper_downloader_req,
        headers={'Authorization': fake_token}
    )

    req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], resp_json['id'])
    falcon_api.mock_req_store.set.assert_called_with(req_store_id, resp_body)
    assert resp_json['status'] == 'VALIDATED'


def test_acquisition_bad_request(falcon_api):
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


# def test_downloader_callback(falcon_api):
#     test_port = 12345
#     os.environ['VCAP_APP_PORT'] = str(test_port)
#     fake_token = 'bearer some+base64+bytes'
#
#     resp_body, headers = simulate_falcon_request(
#         api=falcon_api,
#         path=ACQUISITION_PATH,
#         encoding='utf-8',
#         method='POST',
#         body=json.dumps(TEST_DOWNLOAD_REQUEST),
#         headers=[('Authorization', fake_token)]
#     )
#     resp_json = json.loads(resp_body)
#
#     assert headers.status == falcon.HTTP_202
#     assert dict_is_part_of(resp_json, TEST_DOWNLOAD_REQUEST)
#
#     proper_downloader_req = {
#         'source': TEST_DOWNLOAD_REQUEST['source'],
#         'callback': 'http://localhost:{}{}'.format(test_port, DOWNLOAD_CALLBACK_PATH)
#     }
#     falcon_api.mock_queue.enqueue.assert_called_with(
#         requests.post,
#         url=falcon_api.fake_downloader_url,
#         json=proper_downloader_req,
#         headers={'Authorization': fake_token}
#     )
#
#     req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], resp_json['id'])
#     falcon_api.mock_req_store.set.assert_called_with(req_store_id, resp_body)
#     assert resp_json['status'] == 'VALIDATED'
# TODO test callback from metadata parser
# TODO test getting one entry for an org
# TODO test deleting an entry
# TODO test getting all entries for an org
# TODO test getting all entries as an admin