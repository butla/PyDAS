import json
import os
import pytest

from data_acquisition.cf_app_utils.auth import USER_MANAGEMENT_PATH
from tests.consts import TEST_VCAP_APPLICATION, TEST_VCAP_SERVICES_TEMPLATE
from data_acquisition import DasConfig
from data_acquisition.config import BadConfigurationPathError, NoServiceConfigurationError
from data_acquisition.consts import DOWNLOADER_PATH, METADATA_PARSER_PATH

TEST_VCAP_SERVICES = TEST_VCAP_SERVICES_TEMPLATE.format(
    redis_port=11111,
    redis_password='"some-pass"',
    redis_host='10.10.10.10',
    downloader_host='downloader.example.com',
    metadata_parser_host='metadata-parser.example.com',
    user_management_host='user-management.example.com',
    verification_key_url='http://uaa.example.com/token_key',
)


def test_config_creation():
    os.environ['VCAP_SERVICES'] = TEST_VCAP_SERVICES
    os.environ['VCAP_APPLICATION'] = TEST_VCAP_APPLICATION
    os.environ['VCAP_APP_PORT'] = '12345'
    config = DasConfig.get_config()

    assert config.self_url == 'https://das.example.com'
    assert config.port == 12345

    assert config.redis_port == 11111
    assert config.redis_host == '10.10.10.10'
    assert config.redis_password == 'some-pass'

    assert config.downloader_url == 'http://downloader.example.com' + DOWNLOADER_PATH
    assert config.metadata_parser_url == 'http://metadata-parser.example.com' + METADATA_PARSER_PATH
    assert config.user_management_url == 'http://user-management.example.com' + USER_MANAGEMENT_PATH
    assert config.verification_key_url == 'http://uaa.example.com/token_key'

    assert config is DasConfig.get_config()


def test_config_bad_service():
    with pytest.raises(NoServiceConfigurationError):
        DasConfig._get_service_value(
            json.loads(TEST_VCAP_SERVICES),
            'nonexistent-service/blabla')


def test_config_bad_service_conf_path():
    with pytest.raises(BadConfigurationPathError):
        DasConfig._get_service_value(
            json.loads(TEST_VCAP_SERVICES),
            'requests-store/blabla')
