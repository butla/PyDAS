import json
from urllib.parse import urljoin

import pytest
import requests
import redis

from data_acquisition.consts import (ACQUISITION_PATH, DOWNLOAD_CALLBACK_PATH,
                                     METADATA_PARSER_CALLBACK_PATH)
from data_acquisition.resources import AcquisitionRequest
from .consts import TEST_AUTH_HEADER, TEST_DOWNLOAD_REQUEST
from .utils import dict_is_part_of


def test_acquisition_request(redis_port, das, downloader_imposter):
    # TODO change acquisition endpoint
    response = requests.post(
        _get_das_url(das.port, ACQUISITION_PATH),
        json=TEST_DOWNLOAD_REQUEST,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 202
    req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], response.json()['id'])
    redis_client = redis.Redis(port=redis_port, db=0)
    stored_req = AcquisitionRequest.from_bytes(redis_client.get(req_store_id))
    assert stored_req.status == 'VALIDATED'

    request_to_imposter = downloader_imposter.wait_for_requests()[0]
    # TODO the id needs to be at the end
    assert json.loads(request_to_imposter.body) == {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': urljoin(
            'https://das.example.com',
            DOWNLOAD_CALLBACK_PATH.format(response.json()['id']))
    }
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


@pytest.mark.xfail
def test_download_callback(redis_port, das, metadata_parser_imposter):
    stored_req = AcquisitionRequest(**TEST_DOWNLOAD_REQUEST)

    # TODO use the const
    downloader_callback_req = {
        #'source': 'http://fake-url',
        #'callback': 'http://fake-url',
        'id': 'fake-download-id',
        'state': 'DONE', # can also be FAILED
        'downloadedBytes': 123,
        'savedObjectId': 'fake-saved-id',
        'objectStoreId': 'fake-store-id',
        #'token': TEST_AUTH_HEADER
    }
    req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], downloader_callback_req['id'])
    # TODO make redis client a fixture
    redis_client = redis.Redis(port=redis_port, db=0)
    # adding the acquisition request into redis so it can be read by DAS
    redis_client.set(req_store_id, str(stored_req))

    response = requests.post(
        _get_das_url(das.port, DOWNLOAD_CALLBACK_PATH.format(downloader_callback_req['id'])),
        json=downloader_callback_req,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    stored_req = AcquisitionRequest.from_bytes(redis_client.get(req_store_id))
    assert stored_req.status == 'DOWNLOADED'

    request_to_imposter = metadata_parser_imposter.wait_for_requests()[0]
    metadata_parse_request = dict(TEST_DOWNLOAD_REQUEST)
    metadata_parse_request.update({
        'id': downloader_callback_req['id'],
        'idInObjectStore': 'hdfs://some-fake-hdfs-path',
        'callbackUrl': urljoin('https://das.example.com', METADATA_PARSER_CALLBACK_PATH)
    })
    # MetadataParseRequest req = new MetadataParseRequest();
    # req.setId(request.getId());
    # req.setIdInObjectStore(request.getIdInObjectStore());
    # req.setSource(request.getSource());
    # req.setTitle(request.getTitle());
    # req.setCategory(request.getCategory());
    # req.setOrgUUID(UUID.fromString(request.getOrgUUID()));
    # req.setPublicRequest(request.isPublicRequest());
    # req.setCallbackUrl(new UriTemplate(callbacksUrl).expand("metadata", request.getId()));
    assert json.loads(request_to_imposter.body) == metadata_parse_request
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})
    # TODO refactor this and the previous test

# TODO test redis store
# TODO test callback from metadata parser
# TODO test getting all entries for an org

def _get_das_url(port, path):
    das_url = 'http://localhost:{}'.format(port)
    return urljoin(das_url, path)
