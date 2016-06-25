import copy
from unittest.mock import MagicMock, call

import falcon
import pytest
import responses

from data_acquisition.acquisition_request import AcquisitionRequest, RequestNotFoundError
from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_CALLBACK_PATH, GET_REQUEST_PATH)
from data_acquisition.resources import (get_download_callback_url, get_metadata_callback_url,
                                        AcquisitionRequestsResource)
from tests.consts import (TEST_DOWNLOAD_REQUEST, TEST_DOWNLOAD_CALLBACK, TEST_ACQUISITION_REQ,
                          TEST_ACQUISITION_REQ_JSON, TEST_ORG_UUID, FAKE_PERMISSION_URL)
from tests.utils import FalconApiTestClient

FAKE_TIME = 234.25
FAKE_TIMESTAMP = 234


@pytest.fixture(scope='function')
def test_client(falcon_api):
    return FalconApiTestClient(falcon_api)


@pytest.fixture(scope='function')
def acquisition_requests_resource(das_config, mock_executor, mock_req_store, fake_time):
    return AcquisitionRequestsResource(mock_req_store, mock_executor, das_config)


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
def test_external_service_call_not_ok(acquisition_requests_resource):
    test_url = 'https://some-fake-url/'
    responses.add(responses.POST, test_url, status=404)

    assert not acquisition_requests_resource._external_service_call(
        url=test_url, data={'a': 'b'}, token='bearer fake-token', request_id='some-fake-id')


def test_processing_acquisition_request_for_hdfs(acquisition_requests_resource, mock_req_store):
    # arrange
    mock_enqueue_metadata_req = MagicMock()
    acquisition_requests_resource._enqueue_metadata_request = mock_enqueue_metadata_req

    hdfs_acquisition_req = copy.deepcopy(TEST_ACQUISITION_REQ)
    hdfs_acquisition_req.source = TEST_ACQUISITION_REQ.source.replace('http://', 'hdfs://')
    proper_saved_request = copy.deepcopy(hdfs_acquisition_req)
    proper_saved_request.set_downloaded()
    fake_token = 'bearer asdasdasdasd'

    # act
    acquisition_requests_resource._process_acquisition_request(hdfs_acquisition_req, fake_token)

    # assert
    mock_enqueue_metadata_req.assert_called_with(proper_saved_request, None, fake_token)
    mock_req_store.put.assert_called_with(proper_saved_request)


def test_acquisition_bad_request(test_client):
    broken_request = dict(TEST_DOWNLOAD_REQUEST)
    del broken_request['category']

    _, headers = test_client.post(ACQUISITION_PATH, broken_request)
    assert headers.status == falcon.HTTP_400


def test_downloader_callback_failed(test_client, fake_time, mock_req_store, req_store_get):
    failed_callback_req = dict(TEST_DOWNLOAD_CALLBACK)
    failed_callback_req['state'] = 'ERROR'

    _, response_info = test_client.post(
        path=DOWNLOAD_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data=failed_callback_req)

    assert response_info.status == falcon.HTTP_200

    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    mock_req_store.put.assert_called_with(updated_request)


def test_metadata_callback_failed(test_client, fake_time, mock_req_store, req_store_get):
    _, response_info = test_client.post(
        path=METADATA_PARSER_CALLBACK_PATH.format(req_id=TEST_ACQUISITION_REQ.id),
        data={'state': 'FAILED'})

    assert response_info.status == falcon.HTTP_200
    updated_request = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    updated_request.state = 'ERROR'
    updated_request.timestamps['ERROR'] = FAKE_TIMESTAMP
    mock_req_store.put.assert_called_with(updated_request)


@responses.activate
def test_get_request(test_client, req_store_get, mock_user_management):
    resp_json, resp_info = test_client.get(GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert resp_info.status == falcon.HTTP_200
    assert AcquisitionRequest(**resp_json) == TEST_ACQUISITION_REQ


def test_get_request_not_found(test_client, mock_req_store):
    mock_req_store.get.side_effect = RequestNotFoundError()
    _, response_info = test_client.get(GET_REQUEST_PATH.format(req_id='some-fake-id'))
    assert response_info.status == falcon.HTTP_404


@responses.activate
def test_delete_request(test_client, mock_req_store, req_store_get, mock_user_management):
    response_info = test_client.delete(GET_REQUEST_PATH.format(req_id=TEST_ACQUISITION_REQ.id))
    assert response_info.status == falcon.HTTP_200
    mock_req_store.delete.assert_called_with(TEST_ACQUISITION_REQ)


def test_delete_request_not_found(test_client, mock_req_store):
    mock_req_store.get.side_effect = RequestNotFoundError()
    response_info = test_client.delete(GET_REQUEST_PATH.format(req_id='fake-id'))
    assert response_info.status == falcon.HTTP_404


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

    resp_json, response_info = test_client.get(path=ACQUISITION_PATH,
                                         query_string='orgs=' + ','.join(org_ids))
    returned_requests = [AcquisitionRequest(**req_json) for req_json in resp_json]

    assert response_info.status == falcon.HTTP_200
    assert returned_requests == acquisition_requests * len(org_ids)
    assert mock_req_store.get_for_org.call_args_list == [call(id) for id in org_ids]
