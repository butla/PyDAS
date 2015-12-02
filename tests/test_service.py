import json
import requests

from data_acquisition.consts import ACQUISITION_PATH
from data_acquisition.resources import get_download_callback_url, get_metadata_callback_url
from .consts import (TEST_AUTH_HEADER, TEST_DOWNLOAD_REQUEST, TEST_ACQUISITION_REQ,
                     TEST_DOWNLOAD_CALLBACK)
from .utils import dict_is_part_of


def test_acquisition_request(requests_store, das, downloader_imposter):
    response = requests.post(
        das.base_url + ACQUISITION_PATH,
        json=TEST_DOWNLOAD_REQUEST,
        headers={'Authorization': TEST_AUTH_HEADER}
    )
    req_id = response.json()['id']

    assert response.status_code == 202
    assert requests_store.get(req_id).status == 'VALIDATED'

    request_to_imposter = downloader_imposter.wait_for_requests()[0]
    assert json.loads(request_to_imposter.body) == {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': get_download_callback_url('https://das.example.com', req_id)
    }
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


def test_download_callback(requests_store, das, metadata_parser_imposter):
    requests_store.put(TEST_ACQUISITION_REQ)
    req_id = TEST_ACQUISITION_REQ.id

    response = requests.post(
        get_download_callback_url(das.base_url, req_id=req_id),
        json=TEST_DOWNLOAD_CALLBACK,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    assert requests_store.get(req_id).status == 'DOWNLOADED'

    request_to_imposter = metadata_parser_imposter.wait_for_requests()[0]
    proper_metadata_req = {
        'orgUUID': TEST_ACQUISITION_REQ.orgUUID,
        'publicRequest': TEST_ACQUISITION_REQ.publicRequest,
        'source': TEST_ACQUISITION_REQ.source,
        'category': TEST_ACQUISITION_REQ.category,
        'title': TEST_ACQUISITION_REQ.title,
        'id': req_id,
        'idInObjectStore': TEST_DOWNLOAD_CALLBACK['objectStoreId'],
        'callbackUrl': get_metadata_callback_url('https://das.example.com', req_id)
    }

    assert json.loads(request_to_imposter.body) == proper_metadata_req
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


# TODO test redis store
# TODO test callback from metadata parser
# TODO test getting all entries for an org
# TODO test that middleware is working (invalid token)
