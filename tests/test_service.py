import copy
import json
from urllib.parse import urljoin

import requests

from data_acquisition.consts import ACQUISITION_PATH, UPLOADER_REQUEST_PATH
from data_acquisition.resources import get_download_callback_url, get_metadata_callback_url
from data_acquisition.acquisition_request import AcquisitionRequest
from .consts import (TEST_AUTH_HEADER, TEST_DOWNLOAD_REQUEST, TEST_ACQUISITION_REQ,
                     TEST_DOWNLOAD_CALLBACK, TEST_METADATA_CALLBACK)
from .utils import dict_is_part_of


def test_acquisition_request(req_store_real, das, downloader_imposter):
    response = requests.post(
        das.base_url + ACQUISITION_PATH,
        json=TEST_DOWNLOAD_REQUEST,
        headers={'Authorization': TEST_AUTH_HEADER}
    )
    req_id = response.json()['id']

    assert response.status_code == 202
    assert req_store_real.get(req_id).state == 'VALIDATED'

    request_to_imposter = downloader_imposter.wait_for_requests()[0]
    assert json.loads(request_to_imposter.body) == {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': get_download_callback_url('https://das.example.com', req_id)
    }
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


def test_download_callback(req_store_real, das, metadata_parser_imposter):
    req_store_real.put(TEST_ACQUISITION_REQ)
    req_id = TEST_ACQUISITION_REQ.id

    response = requests.post(
        get_download_callback_url(das.base_url, req_id=req_id),
        json=TEST_DOWNLOAD_CALLBACK,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    assert req_store_real.get(req_id).state == 'DOWNLOADED'

    request_to_imposter = metadata_parser_imposter.wait_for_requests()[0]
    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source,
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': req_id,
        'idInObjectStore': TEST_DOWNLOAD_CALLBACK['savedObjectId'],
        'callbackUrl': get_metadata_callback_url('https://das.example.com', req_id)
    }

    assert json.loads(request_to_imposter.body) == proper_metadata_req
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


def test_metadata_callback(req_store_real, das):
    req_store_real.put(TEST_ACQUISITION_REQ)
    req_id = TEST_ACQUISITION_REQ.id

    response = requests.post(
        get_metadata_callback_url(das.base_url, req_id=req_id),
        json=TEST_METADATA_CALLBACK,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    assert req_store_real.get(req_id).state == 'FINISHED'


def test_uploader_request(req_store_real, das, metadata_parser_imposter):
    test_uploader_req = dict(TEST_DOWNLOAD_REQUEST)
    test_uploader_req.update({
        'idInObjectStore': 'fake-guid/000000_1',
        'objectStoreId': 'hdfs://some-fake-hdfs-path',
    })

    response = requests.post(
        urljoin(das.base_url, UPLOADER_REQUEST_PATH),
        json=test_uploader_req,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    stored_request = req_store_real.get_for_org(test_uploader_req['orgUUID'])[0]
    assert stored_request.state == 'DOWNLOADED'

    request_to_imposter = metadata_parser_imposter.wait_for_requests()[0]
    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source,
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': stored_request.id,
        'idInObjectStore': test_uploader_req['idInObjectStore'],
        'callbackUrl': get_metadata_callback_url('https://das.example.com', stored_request.id)
    }

    assert json.loads(request_to_imposter.body) == proper_metadata_req
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


def test_get_requests(req_store_real, das):
    test_requests = [copy.deepcopy(TEST_ACQUISITION_REQ) for _ in range(3)]
    test_requests[1].id = 'qzawx'
    test_requests[2].orgUUID = 'some-other-org-uuid'
    for test_request in test_requests:
        req_store_real.put(test_request)

    response = requests.get(
        urljoin(das.base_url, ACQUISITION_PATH),
        params={'orgs': TEST_ACQUISITION_REQ.orgUUID},
        headers={'Authorization': TEST_AUTH_HEADER}
    )
    returned_requests = [AcquisitionRequest(**req_json) for req_json in response.json()]

    assert response.status_code == 200
    assert set(returned_requests) == set(test_requests[:-1])

# TODO test that middleware is working (invalid token)
# TODO test that org authorization works
