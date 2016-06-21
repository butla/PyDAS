import copy
import json
from unittest.mock import MagicMock, patch, call
from urllib.parse import urljoin

import falcon
import pytest
import requests
import responses

import data_acquisition.app
from data_acquisition import DasConfig
from data_acquisition.acquisition_request import AcquisitionRequest, RequestNotFoundError
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_PATH, METADATA_PARSER_CALLBACK_PATH,
                                     GET_REQUEST_PATH)
from data_acquisition.resources import (get_download_callback_url, get_metadata_callback_url,
                                        external_service_call, SecretString)
from tests.consts import (TEST_DOWNLOAD_REQUEST, TEST_DOWNLOAD_CALLBACK, TEST_ACQUISITION_REQ,
                          TEST_ACQUISITION_REQ_JSON, TEST_AUTH_HEADER,
                          TEST_ORG_UUID, FAKE_PERMISSION_URL, FAKE_PERMISSION_SERVICE_URL)
from tests.utils import dict_is_part_of, FalconApiTestClient

FAKE_TIME = 234.25
FAKE_TIMESTAMP = 234
TEST_DAS_URL = 'https://my-fake-url'


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
        verification_key_url='http://fake-verification-key-url')


@pytest.fixture
def mock_executor():
    return MagicMock()


@pytest.fixture
def mock_req_store():
    return MagicMock()


@pytest.fixture(scope='function')
def test_client(das_config, mock_executor, mock_req_store):
    api = falcon.API()
    data_acquisition.app.add_resources_to_routes(
        api,
        mock_req_store,
        mock_executor,
        das_config)
    return FalconApiTestClient(api)


@pytest.fixture(scope='function')
def req_store_get(mock_req_store):
    mock_req_store.get.return_value = copy.deepcopy(TEST_ACQUISITION_REQ)
    return mock_req_store.get


@pytest.fixture(scope='function')
def fake_time(monkeypatch):
    monkeypatch.setattr('time.time', lambda: FAKE_TIME)


@pytest.fixture
def mock_user_management():
    responses.add(responses.GET, FAKE_PERMISSION_URL, status=200, json=[
        {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
    ])


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
    mock_post.side_effect = requests.exceptions.ConnectionError()
    assert not external_service_call('https://bla', {'a': 'b'}, SecretString('bearer fake-token'))


@responses.activate
def test_acquisition_request_for_hdfs(test_client, das_config, fake_time, mock_user_management,
                                      mock_req_store, mock_executor):
    # with hdfs:// URI, Metadata Parser will create "idInObjectStore" from "source"
    test_request = copy.deepcopy(TEST_DOWNLOAD_REQUEST)
    test_request['source'] = test_request['source'].replace('http://', 'hdfs://')

    resp_json, headers = test_client.post(ACQUISITION_PATH, test_request)

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
    mock_executor.submit.assert_called_with(
        external_service_call,
        url=das_config.metadata_parser_url,
        data=proper_metadata_req,
        hidden_token=SecretString(TEST_AUTH_HEADER))

    mock_req_store.put.assert_called_with(stored_req)
    assert stored_req.state == 'DOWNLOADED'
    assert stored_req.timestamps['DOWNLOADED'] == FAKE_TIMESTAMP


def test_acquisition_bad_request(test_client):
    broken_request = dict(TEST_DOWNLOAD_REQUEST)
    del broken_request['category']

    _, headers = test_client.post(ACQUISITION_PATH, broken_request)
    assert headers.status == falcon.HTTP_400


def test_downloader_callback_failed(test_client, fake_time, mock_req_store, req_store_get):
    failed_callback_req = dict(TEST_DOWNLOAD_CALLBACK)
    failed_callback_req['state'] = 'ERROR'

    _, headers = test_client.post(
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data=failed_callback_req)

    assert headers.status == falcon.HTTP_200

    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    mock_req_store.put.assert_called_with(updated_request)


def test_metadata_callback_failed(test_client, fake_time, mock_req_store, req_store_get):
    _, headers = test_client.post(
        path=METADATA_PARSER_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data={'state': 'FAILED'})

    assert headers.status == falcon.HTTP_200
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    mock_req_store.put.assert_called_with(updated_request)


@responses.activate
def test_get_request(test_client, req_store_get, mock_user_management):
    resp_json, headers = test_client.get(GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert headers.status == falcon.HTTP_200
    assert AcquisitionRequest(**resp_json) == TEST_ACQUISITION_REQ


def test_get_request_not_found(test_client, mock_req_store):
    mock_req_store.get.side_effect = RequestNotFoundError()
    _, headers = test_client.get(GET_REQUEST_PATH.format(req_id='some-fake-id'))
    assert headers.status == falcon.HTTP_404


@responses.activate
def test_delete_request(test_client, mock_req_store, req_store_get, mock_user_management):
    headers = test_client.delete(GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert headers.status == falcon.HTTP_200
    mock_req_store.delete.assert_called_with(TEST_ACQUISITION_REQ)


def test_delete_request_not_found(test_client, mock_req_store):
    mock_req_store.get.side_effect = RequestNotFoundError()
    headers = test_client.delete(GET_REQUEST_PATH.format(req_id='fake-id'))
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
def test_get_requests_for_org(org_ids, acquisition_requests, test_client, mock_req_store):
    responses.add(
        responses.GET,
        FAKE_PERMISSION_URL,
        status=200,
        json=[{'organization': {'metadata': {'guid': id}}} for id in org_ids])

    mock_req_store.get_for_org.return_value = acquisition_requests

    resp_json, headers = test_client.get(path=ACQUISITION_PATH,
                                         query_string='orgs=' + ','.join(org_ids))
    returned_requests = [AcquisitionRequest(**req_json) for req_json in resp_json]

    assert headers.status == falcon.HTTP_200
    assert returned_requests == acquisition_requests * len(org_ids)
    assert mock_req_store.get_for_org.call_args_list == [call(id) for id in org_ids]
