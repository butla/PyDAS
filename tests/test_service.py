import json
from urllib.parse import urljoin

import requests
import redis

from data_acquisition.consts import ACQUISITION_PATH, DOWNLOAD_CALLBACK_PATH
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
    assert redis_client.get(req_store_id)

    request_to_imposter = downloader_imposter.wait_for_requests()[0]
    assert json.loads(request_to_imposter.body) == {
        'source': TEST_DOWNLOAD_REQUEST['source'],
        'callback': 'http://localhost:{}{}'.format(das.port, DOWNLOAD_CALLBACK_PATH)
    }
    assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})


# needs to run after test_acquisition_request
def test_download_callback(redis_port, das, downloader_imposter):
    # TODO this callback should only update the state
    stored_req = None

    downloader_callback_req = {
        'source': 'http://fake-url',
        'callback': 'http://fake-url',
        'id': 'fake-id',
        'state': 'DONE', # can also be FAILED
        'downloadedBytes': 123,
        'savedObjectId': 'fake-saved-id',
        'objectStoreId': 'fake-store-id',
        'token': TEST_AUTH_HEADER
    }

    # TODO what is sent?
    response = requests.post(
        _get_das_url(das.port, DOWNLOAD_CALLBACK_PATH),
        json=TEST_DOWNLOAD_REQUEST,
        headers={'Authorization': TEST_AUTH_HEADER}
    )

    assert response.status_code == 200
    # req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], response.json()['id'])
    # redis_client = redis.Redis(port=redis_port, db=0)
    # assert redis_client.get(req_store_id)
    #
    # request_to_imposter = downloader_imposter.wait_for_requests()[0]
    # assert json.loads(request_to_imposter.body) == {
    #     'source': TEST_DOWNLOAD_REQUEST['source'],
    #     'callback': 'http://localhost:{}{}'.format(das.port, DOWNLOAD_CALLBACK_PATH)
    # }
    # assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})

# TODO test callback from metadata parser
# TODO test getting all entries for an org

def _get_das_url(port, path):
    das_url = 'http://localhost:{}'.format(port)
    return urljoin(das_url, path)