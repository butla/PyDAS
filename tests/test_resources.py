import copy
import json
from unittest.mock import MagicMock, patch
from urllib.parse import urljoin

import responses
import falcon
import pytest

from data_acquisition import DasConfig
from data_acquisition.acquisition_request import AcquisitionRequest
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_PATH, METADATA_PARSER_CALLBACK_PATH)
from data_acquisition.resources import (AcquisitionRequestsResource, DownloadCallbackResource,
                                        MetadataCallbackResource, get_download_callback_url,
                                        get_metadata_callback_url, external_service_call,
                                        SecretString)
from .consts import (TEST_DOWNLOAD_REQUEST, TEST_DOWNLOAD_CALLBACK, TEST_ACQUISITION_REQ,
                     TEST_ACQUISITION_REQ_JSON, TEST_METADATA_CALLBACK, TEST_AUTH_HEADER,
                     TEST_ORG_UUID, FAKE_PERMISSION_URL, FAKE_PERMISSION_SERVICE_URL)
from .utils import dict_is_part_of, simulate_falcon_request


FAKE_TIME = 234.25
FAKE_TIMESTAMP = 234


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
    api.add_route(
        METADATA_PARSER_CALLBACK_PATH,
        MetadataCallbackResource(
            req_store=api.mock_req_store,
            config=das_config)
    )
    return api


@pytest.fixture(scope='function')
def req_store_get(falcon_api):
    falcon_api.mock_req_store.get.return_value = copy.deepcopy(TEST_ACQUISITION_REQ)
    return falcon_api.mock_req_store.get


@pytest.fixture(scope='function')
def fake_time(monkeypatch):
    monkeypatch.setattr('time.time', lambda: FAKE_TIME)


def _simulate_falcon_post(api, path, data):
    resp_body, headers = simulate_falcon_request(
        api=api,
        path=path,
        body=json.dumps(data),
        encoding='utf-8',
        method='POST',
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )
    resp_json = json.loads(resp_body) if resp_body else None
    return resp_json, headers


def test_get_download_callback_url():
    callback_url = get_download_callback_url('https://some-test-das-url', 'some-test-id')
    assert callback_url == 'https://some-test-das-url/v1/das/callback/downloader/some-test-id'


def test_get_metadata_callback_url():
    callback_url = get_metadata_callback_url('https://some-test-das-url', 'some-test-id')
    assert callback_url == 'https://some-test-das-url/v1/das/callback/metadata/some-test-id'


@responses.activate
def test_external_service_call_ok():
    test_url = 'https://some-fake-url/'
    test_token = 'bearer fake-token'
    test_json = {'a': 'b'}
    responses.add(responses.POST, test_url, status=200)

    assert external_service_call(test_url, test_json, SecretString(test_token))
    assert responses.calls[0].request.url == test_url
    assert responses.calls[0].request.body == json.dumps(test_json)
    assert responses.calls[0].request.headers['Authorization'] == test_token


@responses.activate
def test_external_service_call_not_ok():
    test_url = 'https://some-fake-url/'
    responses.add(responses.POST, test_url, status=404)

    assert not external_service_call(test_url, {'a': 'b'}, SecretString('bearer fake-token'))


@patch('data_acquisition.resources.requests.post')
def test_external_service_call_error(mock_post):
    mock_post.side_effect = Exception('test exception')
    assert not external_service_call('https://bla', {'a': 'b'}, SecretString('bearer fake-token'))


@responses.activate
def test_acquisition_request(falcon_api, das_config, fake_time):
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=200, json=[
        {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
    ])

    resp_json, headers = _simulate_falcon_post(falcon_api, ACQUISITION_PATH, TEST_DOWNLOAD_REQUEST)

    assert headers.status == falcon.HTTP_202
    assert dict_is_part_of(resp_json, TEST_DOWNLOAD_REQUEST)

    proper_downloader_req = {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': get_download_callback_url('https://my-fake-url', resp_json['id'])
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        external_service_call,
        url=das_config.downloader_url,
        json=proper_downloader_req,
        hidden_token=SecretString(TEST_AUTH_HEADER)
    )

    stored_req = AcquisitionRequest(**resp_json)
    falcon_api.mock_req_store.put.assert_called_with(stored_req)
    assert stored_req.state == 'VALIDATED'
    assert stored_req.timestamps['VALIDATED'] == FAKE_TIMESTAMP


def test_acquisition_bad_request(falcon_api):
    broken_request = dict(TEST_DOWNLOAD_REQUEST)
    del broken_request['category']

    __, headers = _simulate_falcon_post(falcon_api, ACQUISITION_PATH, broken_request)
    assert headers.status == falcon.HTTP_400


def test_downloader_callback_ok(falcon_api, das_config, fake_time, req_store_get):
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

    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data=TEST_DOWNLOAD_CALLBACK
    )

    assert headers.status == falcon.HTTP_200

    falcon_api.mock_queue.enqueue.assert_called_with(
        external_service_call,
        url=das_config.metadata_parser_url,
        json=proper_metadata_req,
        hidden_token=SecretString(TEST_AUTH_HEADER)
    )

    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'DOWNLOADED'
    updated_request.timestamps['DOWNLOADED'] = FAKE_TIMESTAMP
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_downloader_callback_failed(falcon_api, fake_time, req_store_get):
    failed_callback_req = dict(TEST_DOWNLOAD_CALLBACK)
    failed_callback_req['state'] = 'ERROR'

    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data=failed_callback_req
    )

    assert headers.status == falcon.HTTP_200

    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_downloader_callback_bad_request(falcon_api):
    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data={'some': 'nonsense'}
    )
    assert headers.status == falcon.HTTP_400


def test_metadata_callback_ok(falcon_api, fake_time, req_store_get):
    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=METADATA_PARSER_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data=TEST_METADATA_CALLBACK
    )

    assert headers.status == falcon.HTTP_200
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'FINISHED'
    updated_request.timestamps['FINISHED'] = FAKE_TIMESTAMP
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_metadata_callback_failed(falcon_api, fake_time, req_store_get):
    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=METADATA_PARSER_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data={'state': 'FAILED'}
    )

    assert headers.status == falcon.HTTP_200
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    falcon_api.mock_req_store.put.assert_called_with(updated_request)


def test_metadata_callback_bad_request(falcon_api):
    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=METADATA_PARSER_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data={'some': 'nonsense'}
    )
    assert headers.status == falcon.HTTP_400


# TODO test getting one entry for an org
# TODO test deleting an entry
# TODO test getting all entries for an org
# TODO test getting all entries as an admin