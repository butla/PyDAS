import copy
import json
from unittest.mock import MagicMock

import pytest

from data_acquisition.acquisition_request import AcquisitionRequest, AcquisitionRequestStore
from tests.consts import TEST_ACQUISITION_REQ, TEST_ACQUISITION_REQ_STR, TEST_ACQUISITION_REQ_JSON


@pytest.fixture
def redis_mock():
    return MagicMock()


@pytest.fixture
def req_store(redis_mock):
    return AcquisitionRequestStore(redis_mock)


def test_get_request_redis_id(req_store):
    request_redis_id = req_store.get_request_redis_id(TEST_ACQUISITION_REQ)
    assert request_redis_id == '{}:{}'.format(TEST_ACQUISITION_REQ.orgUUID, TEST_ACQUISITION_REQ.id)


def test_put(req_store, redis_mock):
    req_store.put(TEST_ACQUISITION_REQ)
    redis_mock.hset.assert_called_with(
        AcquisitionRequestStore.REDIS_HASH_NAME,
        AcquisitionRequestStore.get_request_redis_id(TEST_ACQUISITION_REQ),
        TEST_ACQUISITION_REQ_STR)


def _get_store_id(acquisition_req):
    return '{}:{}'.format(acquisition_req.orgUUID, acquisition_req.id).encode()


def test_get_for_org(req_store, redis_mock):
    test_requests = [copy.deepcopy(TEST_ACQUISITION_REQ) for _ in range(3)]
    test_requests[1].orgUUID = 'other-fake-uuid'
    test_requests[2].id = 'other-fake-id'
    redis_mock.hgetall.return_value = {_get_store_id(req): str(req).encode()
                                       for req in test_requests}

    acquisition_requests = req_store.get_for_org('fake-org-uuid')

    assert test_requests[0] in acquisition_requests
    assert test_requests[2] in acquisition_requests


def test_get_from_old_base(req_store, redis_mock):
    old_request = dict(TEST_ACQUISITION_REQ_JSON)
    old_request.update({'unnecessary_field': 'blablabla'})
    redis_mock.hgetall.return_value = {b'fake-org-uuid:fake-id': json.dumps(old_request).encode()}

    acquisition_req = req_store.get('fake-id')

    assert acquisition_req == AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)
    redis_mock.hgetall.assert_called_with(AcquisitionRequestStore.REDIS_HASH_NAME)