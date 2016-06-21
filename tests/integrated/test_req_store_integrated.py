import pytest

from data_acquisition.acquisition_request import (AcquisitionRequest, AcquisitionRequestStore,
                                                  RequestNotFoundError)
from tests.consts import TEST_ACQUISITION_REQ, TEST_ACQUISITION_REQ_JSON


@pytest.fixture
def stored_request_real(redis_client):
    new_req = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    new_req.timestamps['VALIDATED'] = 1449523225
    redis_client.hset(
        AcquisitionRequestStore.REDIS_HASH_NAME,
        AcquisitionRequestStore.get_request_redis_id(TEST_ACQUISITION_REQ),
        str(new_req))
    return new_req


def test_get(req_store_real, stored_request_real):
    acquisition_req = req_store_real.get(TEST_ACQUISITION_REQ.id)
    assert acquisition_req == stored_request_real


def test_get_not_found(req_store_real):
    with pytest.raises(RequestNotFoundError):
        req_store_real.get('fake-id')


def test_delete(req_store_real, redis_client, stored_request_real):
    req_store_real.delete(TEST_ACQUISITION_REQ)
    assert not redis_client.hexists(
        AcquisitionRequestStore.REDIS_HASH_NAME,
        AcquisitionRequestStore.get_request_redis_id(TEST_ACQUISITION_REQ))
