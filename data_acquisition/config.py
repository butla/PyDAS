"""
Configuration related stuff.
"""
import functools
import json
import os
from urllib.parse import urljoin

from .cf_app_utils.auth import USER_MANAGEMENT_PATH
from .consts import DOWNLOADER_PATH, METADATA_PARSER_PATH


# TODO most of this class should be extracted as a base class for other configuration objects
class DasConfig:

    """
    Configuration for the application.
    The values need to be taken from environment variables.
    """

    _conf_obj = None

    def __init__(
            self,
            self_url=None,
            port=None,
            redis_port=None,
            redis_host=None,
            redis_password=None,
            downloader_url=None,
            metadata_parser_url=None,
            user_management_url=None,
            verification_key_url=None):
        """
        Should not be used (instantiated) directly outside of tests.
        Use `get_config`.
        """
        self.self_url = self_url
        self.port = port
        self.redis_port = redis_port
        self.redis_host = redis_host
        self.redis_password = redis_password
        self.downloader_url = downloader_url
        self.metadata_parser_url = metadata_parser_url
        self.user_management_url = user_management_url
        self.verification_key_url = verification_key_url

    @classmethod
    def get_config(cls):
        """
        :return: The configuration object for the application.
        :rtype: DasConfig
        """
        if not cls._conf_obj:
            cls._conf_obj = cls._gather_configuration()
        return cls._conf_obj

    @staticmethod
    def _gather_configuration():
        """
        :return: The configuration from environment variables wrapped in an object.
        :rtype: DasConfig
        """
        vcap_services = json.loads(os.environ['VCAP_SERVICES'])
        vcap_application = json.loads(os.environ['VCAP_APPLICATION'])
        get_serv_value = functools.partial(DasConfig._get_service_value, vcap_services)

        downloader_url = urljoin(
            get_serv_value('downloader/credentials/url'),
            DOWNLOADER_PATH
        )
        metadata_parser_url = urljoin(
            get_serv_value('metadataparser/credentials/url'),
            METADATA_PARSER_PATH
        )
        user_management_url = urljoin(
            get_serv_value('user-management/credentials/host'),
            USER_MANAGEMENT_PATH
        )
        return DasConfig(
            self_url='https://' + vcap_application['uris'][0],
            port=int(os.environ['VCAP_APP_PORT']),
            redis_host=get_serv_value('requests-store/credentials/hostname'),
            redis_port=int(get_serv_value('requests-store/credentials/port')),
            redis_password=get_serv_value('requests-store/credentials/password'),
            downloader_url=downloader_url,
            metadata_parser_url=metadata_parser_url,
            user_management_url=user_management_url,
            verification_key_url=get_serv_value('sso/credentials/tokenKey')
        )

    @staticmethod
    def _get_service_value(vcap_services, var_path):
        """
        :param dict vcap_services: JSON deserialized from VCAP_SERVICES env variable
        :param str var_path: path to the variable within the JSON.
        First part needs to be the service name, e.g. "my-redis/credentials/port".
        :return: The configuration value.
        :raises NoServiceConfigurationError: When the first part of the path is not found.
        """
        path_parts = var_path.split('/')
        service_name = path_parts[0]
        service_conf_path = path_parts[1:]
        service_conf = DasConfig._get_service_by_name(vcap_services, service_name)

        service_value = service_conf
        for path_part in service_conf_path:
            try:
                service_value = service_value[path_part]
            except KeyError:
                raise BadConfigurationPathError(
                    'Configuration value {} in service {} not found.'.format(
                        path_parts,
                        service_conf_path))
        return service_value


    @staticmethod
    def _get_service_by_name(vcap_services, name):
        """
        :param dict vcap_services: JSON deserialized from VCAP_SERVICES env variable
        :param str name: name of the service, whether normal or user-provided.
        :return: The dictionary with the service configuration (including the name field).
        :rtype: dict
        :raises NoServiceConfigurationError: when service with the given name not found
        """
        for service_list in vcap_services.values():
            try:
                return next(service for service in service_list if service['name'] == name)
            except StopIteration:
                continue
        raise NoServiceConfigurationError('No service in config of name: {}'.format(name))


class NoServiceConfigurationError(Exception):
    """
    Service configuration was not found in the environment variables.
    """
    pass


class BadConfigurationPathError(Exception):
    """
    Path of configuration value is incorrect.
    """
    pass
