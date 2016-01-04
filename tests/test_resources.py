import copy
import json
from unittest.mock import MagicMock, patch, call
from urllib.parse import urljoin

import responses
import falcon
import pytest

from data_acquisition import DasConfig
from data_acquisition.acquisition_request import AcquisitionRequest, RequestNotFoundError
import data_acquisition.app
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_PATH, METADATA_PARSER_CALLBACK_PATH,
                                     UPLOADER_REQUEST_PATH, GET_REQUEST_PATH)
from data_acquisition.resources import (get_download_callback_url, get_metadata_callback_url,
                                        external_service_call, SecretString)
from .consts import (TEST_DOWNLOAD_REQUEST, TEST_DOWNLOAD_CALLBACK, TEST_ACQUISITION_REQ,
                     TEST_ACQUISITION_REQ_JSON, TEST_METADATA_CALLBACK, TEST_AUTH_HEADER,
                     TEST_ORG_UUID, FAKE_PERMISSION_URL, FAKE_PERMISSION_SERVICE_URL)
from .utils import dict_is_part_of, simulate_falcon_request


FAKE_TIME = 234.25
FAKE_TIMESTAMP = 234
TEST_DAS_URL = 'https://my-fake-url'


class MockApi(falcon.API):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock_queue = MagicMock()
        self.mock_req_store = MagicMock()


@pytest.fixture(scope='function')
def das_config():
    return DasConfig(
        self_url=TEST_DAS_URL,
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
    data_acquisition.app.add_resources_to_routes(
        api,
        api.mock_req_store,
        api.mock_queue,
        das_config)
    return api


@pytest.fixture(scope='function')
def req_store_get(falcon_api):
    falcon_api.mock_req_store.get.return_value = copy.deepcopy(TEST_ACQUISITION_REQ)
    return falcon_api.mock_req_store.get


@pytest.fixture(scope='function')
def fake_time(monkeypatch):
    monkeypatch.setattr('time.time', lambda: FAKE_TIME)


@pytest.fixture
def mock_user_management():
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=200, json=[
        {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
    ])


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
def test_acquisition_request(falcon_api, das_config, fake_time, mock_user_management):
    resp_json, headers = _simulate_falcon_post(falcon_api, ACQUISITION_PATH, TEST_DOWNLOAD_REQUEST)

    assert headers.status == falcon.HTTP_202
    assert dict_is_part_of(resp_json, TEST_DOWNLOAD_REQUEST)

    proper_downloader_req = {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': get_download_callback_url(TEST_DAS_URL, resp_json['id'])
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        external_service_call,
        url=das_config.downloader_url,
        data=proper_downloader_req,
        hidden_token=SecretString(TEST_AUTH_HEADER)
    )

    stored_req = AcquisitionRequest(**resp_json)
    falcon_api.mock_req_store.put.assert_called_with(stored_req)
    assert stored_req.state == 'VALIDATED'
    assert stored_req.timestamps['VALIDATED'] == FAKE_TIMESTAMP


@responses.activate
def test_acquisition_request_for_hdfs(falcon_api, das_config, fake_time, mock_user_management):
    # with hdfs:// URI, Metadata Parser will create "idInObjectStore" from "source"
    test_request = copy.deepcopy(TEST_DOWNLOAD_REQUEST)
    test_request['source'] = test_request['source'].replace('http://', 'hdfs://')

    resp_json, headers = _simulate_falcon_post(falcon_api, ACQUISITION_PATH, test_request)

    assert headers.status == falcon.HTTP_202
    assert dict_is_part_of(resp_json, test_request)

    stored_req = AcquisitionRequest(**resp_json)
    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source.replace('http://', 'hdfs://'),
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': stored_req.id,
        'callbackUrl': get_metadata_callback_url(TEST_DAS_URL, stored_req.id)
    }
    falcon_api.mock_queue.enqueue.assert_called_with(
        external_service_call,
        url=das_config.metadata_parser_url,
        data=proper_metadata_req,
        hidden_token=SecretString(TEST_AUTH_HEADER)
    )

    falcon_api.mock_req_store.put.assert_called_with(stored_req)
    assert stored_req.state == 'DOWNLOADED'
    assert stored_req.timestamps['DOWNLOADED'] == FAKE_TIMESTAMP


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
        'idInObjectStore': TEST_DOWNLOAD_CALLBACK['savedObjectId'],
        'callbackUrl': get_metadata_callback_url(TEST_DAS_URL, TEST_ACQUISITION_REQ.id)
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
        data=proper_metadata_req,
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


def test_uploader_request_ok(falcon_api, das_config, fake_time):
    test_uploader_req = dict(TEST_DOWNLOAD_REQUEST)
    test_uploader_req.update({
        'idInObjectStore': 'fake-guid/000000_1',
        'objectStoreId': 'hdfs://some-fake-hdfs-path',
    })

    __, headers = _simulate_falcon_post(
        api=falcon_api,
        path=UPLOADER_REQUEST_PATH,
        data=test_uploader_req
    )

    assert headers.status == falcon.HTTP_200

    stored_req = falcon_api.mock_req_store.put.call_args[0][0]
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'DOWNLOADED'
    updated_request.timestamps['DOWNLOADED'] = FAKE_TIMESTAMP
    updated_request.id = stored_req.id
    assert stored_req == updated_request

    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source,
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': stored_req.id,
        'idInObjectStore': test_uploader_req['idInObjectStore'],
        'callbackUrl': get_metadata_callback_url(TEST_DAS_URL, stored_req.id)
    }

    falcon_api.mock_queue.enqueue.assert_called_with(
        external_service_call,
        url=das_config.metadata_parser_url,
        data=proper_metadata_req,
        hidden_token=SecretString(TEST_AUTH_HEADER)
    )


def _simulate_falcon_get(api, path, query_string=''):
    resp_body, headers = simulate_falcon_request(
        api=api,
        path=path,
        query_string=query_string,
        encoding='utf-8',
        method='GET',
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )
    resp_json = json.loads(resp_body) if resp_body else None
    return resp_json, headers


@responses.activate
def test_get_request(falcon_api, req_store_get, mock_user_management):
    resp_json, headers = _simulate_falcon_get(
        api=falcon_api,
        path=GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert headers.status == falcon.HTTP_200
    assert AcquisitionRequest(**resp_json) == TEST_ACQUISITION_REQ


def test_get_request_not_found(falcon_api):
    falcon_api.mock_req_store.get.side_effect = RequestNotFoundError()
    __, headers = _simulate_falcon_get(
        api=falcon_api,
        path=GET_REQUEST_PATH.format(req_id='some-fake-id'))
    assert headers.status == falcon.HTTP_404


def _simulate_falcon_delete(api, path):
    __, headers = simulate_falcon_request(
        api=api,
        path=path,
        encoding='utf-8',
        method='DELETE',
        headers=[('Authorization', TEST_AUTH_HEADER)]
    )
    return headers


@responses.activate
def test_delete_request(falcon_api, req_store_get, mock_user_management):
    headers = _simulate_falcon_delete(
        falcon_api,
        GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert headers.status == falcon.HTTP_200
    falcon_api.mock_req_store.delete.assert_called_with(TEST_ACQUISITION_REQ)


def test_delete_request_not_found(falcon_api):
    falcon_api.mock_req_store.get.side_effect = RequestNotFoundError()
    headers = _simulate_falcon_delete(
        falcon_api,
        GET_REQUEST_PATH.format(req_id='fake-id'))
    assert headers.status == falcon.HTTP_404


@responses.activate
@pytest.mark.parametrize('org_ids', [
    ['id-1'],
    ['id-1', 'id-2'],
    ['id-1', 'id-2', 'id-3'],
])
@pytest.mark.parametrize('acquisition_requests', [
    [TEST_ACQUISITION_REQ],
    [TEST_ACQUISITION_REQ, TEST_ACQUISITION_REQ]
])
def test_get_requests_for_org(org_ids, acquisition_requests, falcon_api):
    responses.add(
        responses.GET,
        FAKE_PERMISSION_URL,
        status=200,
        json=[{'organization': {'metadata': {'guid': id}}} for id in org_ids])

    falcon_api.mock_req_store.get_for_org.return_value = acquisition_requests

    resp_json, headers = _simulate_falcon_get(
        api=falcon_api,
        path=ACQUISITION_PATH,
        query_string='orgs=' + ','.join(org_ids)
    )
    returned_requests = [AcquisitionRequest(**req_json) for req_json in resp_json]

    assert headers.status == falcon.HTTP_200
    assert returned_requests == acquisition_requests * len(org_ids)
    assert falcon_api.mock_req_store.get_for_org.call_args_list == [call(id) for id in org_ids]
