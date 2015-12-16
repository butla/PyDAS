import json
from unittest.mock import MagicMock

import pytest

from data_acquisition.acquisition_request import AcquisitionRequest, AcquisitionRequestStore
from .consts import TEST_ACQUISITION_REQ, TEST_ACQUISITION_REQ_STR, TEST_ACQUISITION_REQ_JSON


@pytest.fixture
def redis_mock():
    return MagicMock()


@pytest.fixture
def req_store(redis_mock):
    return AcquisitionRequestStore(redis_mock)


@pytest.fixture
def req_store_real(redis_client):
    return AcquisitionRequestStore(redis_client)


def test_put(req_store, redis_mock):
    req_store.put(TEST_ACQUISITION_REQ)
    redis_mock.set.assert_called_with(
        'fake-org-uuid:fake-id',
        TEST_ACQUISITION_REQ_STR)


def test_get(req_store_real, redis_client):
    new_req = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    new_req.timestamps['VALIDATED'] = 1449523225

    redis_client.set('fake-org-uuid:fake-id', str(new_req))
    acquisition_req = req_store_real.get('fake-id')

    assert acquisition_req == new_req


def test_get_from_old_base(req_store_real, redis_client):
    old_request = dict(TEST_ACQUISITION_REQ_JSON)
    old_request.update({'unnecessary_field': 'blablabla'})
    redis_client.set('fake-org-uuid:fake-id', json.dumps(old_request))

    acquisition_req = req_store_real.get('fake-id')
    assert TEST_ACQUISITION_REQ_STR == str(acquisition_req)
