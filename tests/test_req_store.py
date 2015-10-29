import json
from unittest.mock import MagicMock

import pytest

from data_acquisition.resources import AcquisitionRequestStore, AcquisitionRequest

TEST_ACQUISITION_REQ_JSON = {
    'title': 'My test download',
    'orgUUID': 'fake-org-uuid',
    'publicRequest': True,
    'source': 'http://some-fake-url',
    'category': 'science',
    'status': 'VALIDATED',
    'id': 'fake-id'
}

TEST_ACQUISITION_REQ = AcquisitionRequest(**TEST_ACQUISITION_REQ_JSON)

TEST_ACQUISITION_REQ_STR = str(TEST_ACQUISITION_REQ)


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
    redis_client.put(
        'fake-org-uuid:fake-id',
        TEST_ACQUISITION_REQ_STR
    )

    acquisition_req = req_store_real.get('fake-id')

    assert TEST_ACQUISITION_REQ_STR == str(acquisition_req)