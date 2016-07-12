from unittest.mock import MagicMock
from urllib.parse import urljoin

import pytest

import data_acquisition.app
from data_acquisition import DasConfig
from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from data_acquisition.consts import DOWNLOADER_PATH, METADATA_PARSER_PATH
from tests.consts import FAKE_PERMISSION_SERVICE_URL


@pytest.fixture(scope='function')
def das_config():
    return DasConfig(
        self_url='http://my-fake-url',
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


@pytest.fixture
def das_api(mock_req_store, mock_executor, das_config):
    return data_acquisition.app.DasApi(mock_req_store, mock_executor, das_config)


@pytest.fixture(scope='function')
def falcon_api(das_api):
    return das_api.api
