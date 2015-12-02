import json
from unittest.mock import MagicMock
from urllib.parse import urljoin

import responses
import requests
import falcon
import pytest

from data_acquisition import DasConfig
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_PATH)
from data_acquisition.resources import (AcquisitionRequestsResource, DownloadCallbackResource,
                                        AcquisitionRequest, get_download_callback_url,
                                        get_metadata_callback_url)
from .consts import (TEST_DOWNLOAD_REQUEST, TEST_DOWNLOAD_CALLBACK, TEST_ACQUISITION_REQ,
                     TEST_ACQUISITION_REQ_JSON, TEST_AUTH_HEADER, TEST_ORG_UUID,
                     FAKE_PERMISSION_URL, FAKE_PERMISSION_SERVICE_URL)
from .utils import dict_is_part_of, simulate_falcon_request


class MockApi(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_queue = MagicMock()
        self.mock_req_store = MagicMock()


@pytest.fixture(scope='function')
def das_config():
    return DasConfig(
        self_url='https://my-fake-url',
        port=12345,
        redis_host='redis.example.com',
        redis_port=54321,
        redis_password='secret-password',
        downloader_url=urljoin('https://fake-downloader-url', DOWNLOADER_PATH),
        metadata_parser_url=urljoin('https://fake-metadata-url', METADATA_PARSER_PATH),
        user_management_url=urljoin(FAKE_PERMISSION_SERVICE_URL, USER_MANAGEMENT_PATH),
        verification_key_url='http://fake-verification-key-url'
    )


@pytest.fixture(scope='function')
def falcon_api(das_config):
    api = MockApi()
    api.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(
            req_store=api.mock_req_store,
            queue=api.mock_queue,
            config=das_config)
    )
    api.add_route(
        DOWNLOAD_CALLBACK_PATH,
        DownloadCallbackResource(
            req_store=api.mock_req_store,
            queue=api.mock_queue,
            config=das_config)
    )
    return api


def test_get_download_callback_url():
    callback_url = get_download_callback_url('https://some-test-das-url', 'some-test-id')
    assert callback_url == 'https://some-test-das-url/v1/das/callback/downloader/some-test-id'


def test_get_metadata_callback_url():
    callback_url = get_metadata_callback_url('https://some-test-das-url', 'some-test-id')
    assert callback_url == 'https://some-test-das-url/v1/das/callback/metadata/some-test-id'


@responses.activate
def test_acquisition_request(falcon_api, das_config):
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=200, json=[
        {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
    ])

    resp_body, headers = simulate_falcon_request(
        api=falcon_api,
        path=ACQUISITION_PATH,
        encoding='utf-8',
        method='POST',
        body=json.dumps(TEST_DOWNLOAD_REQUEST),
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )
    resp_json = json.loads(resp_body)

    assert headers.status == falcon.HTTP_202
    assert dict_is_part_of(resp_json, TEST_DOWNLOAD_REQUEST)

    proper_downloader_req = {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': get_download_callback_url('https://my-fake-url', resp_json['id'])
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        requests.post,
        url=das_config.downloader_url,
        json=proper_downloader_req,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    falcon_api.mock_req_store.put.assert_called_with(AcquisitionRequest(**resp_json))
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


def test_downloader_callback_ok(falcon_api, das_config):
    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source,
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': TEST_ACQUISITION_REQ.id,
        'idInObjectStore': TEST_DOWNLOAD_CALLBACK['objectStoreId'],
        'callbackUrl': get_metadata_callback_url('https://my-fake-url', TEST_ACQUISITION_REQ.id)
    }
    falcon_api.mock_req_store.get.return_value = TEST_ACQUISITION_REQ

    _, headers = simulate_falcon_request(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        encoding='utf-8',
        method='POST',
        body=json.dumps(TEST_DOWNLOAD_CALLBACK),
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )

    assert headers.status == falcon.HTTP_200

    falcon_api.mock_queue.enqueue.assert_called_with(
        requests.post,
        url=das_config.metadata_parser_url,
        json=proper_metadata_req,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    falcon_api.mock_req_store.get.assert_called_with(TEST_DOWNLOAD_CALLBACK['id'])
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.status = 'DOWNLOADED'
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_downloader_callback_failed_request(falcon_api):
    falcon_api.mock_req_store.get.return_value = TEST_ACQUISITION_REQ
    failed_callback_req = dict(TEST_DOWNLOAD_CALLBACK)
    failed_callback_req['state'] = 'ERROR'

    _, headers = simulate_falcon_request(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        encoding='utf-8',
        method='POST',
        body=json.dumps(failed_callback_req),
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )

    assert headers.status == falcon.HTTP_200

    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.status = 'ERROR'
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_downloader_callback_bad_request(falcon_api):
    _, headers = simulate_falcon_request(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        encoding='utf-8',
        method='POST',
        body=json.dumps({'some': 'nonsense'}),
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )
    assert headers.status == falcon.HTTP_400

# TODO test callback from metadata parser
# TODO test getting one entry for an org
# TODO test deleting an entry
# TODO test getting all entries for an org
# TODO test getting all entries as an admin