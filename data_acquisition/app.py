"""
Application for downloading data sets from the web.
This file is used to create the WSGI app that can be embedded in a container.
"""

from concurrent.futures import ThreadPoolExecutor
import logging

import falcon
import redis

from .cf_app_utils.auth.falcon import JwtMiddleware
from .cf_app_utils import configure_logging
from .config import DasConfig
from .consts import (ACQUISITION_PATH, DOWNLOAD_CALLBACK_PATH, UPLOADER_REQUEST_PATH,
                     METADATA_PARSER_CALLBACK_PATH, GET_REQUEST_PATH)
from .acquisition_request import AcquisitionRequestStore
from .resources import (AcquisitionResource, RequestManagementResource,
                        DownloadCallbackResource, UploaderResource, MetadataCallbackResource)


class DasApi:
    """Creates a Falcon API with DAS resources on proper routes.
    Eases testing of the resources by allowing to switch them out.

    Args:
        requests_store (`data_acquisition.acquisition_request.AcquisitionRequestStore`):
        executor (`concurrent.futures.Executor`): Object that will run background jobs for the
            application.
        config (`data_acquisition.DasConfig`): Configuration object for the application.
        middleware: An object conforming to Falcon middleware specifications.
    """

    def __init__(self, requests_store, executor, config, middleware=None):
        self.middleware = middleware

        self.acquisition_res = AcquisitionResource(requests_store, executor, config)
        self.request_management_res = RequestManagementResource(requests_store, config)
        self.download_callback_res = DownloadCallbackResource(requests_store, executor, config)
        self.metadata_callback_res = MetadataCallbackResource(requests_store, config)
        self.uploader_res = UploaderResource(requests_store, executor, config)

    def get_falcon_api(self):
        """
        Returns:
            `falcon.API`: A fully configured Falcon application.
        """
        api = falcon.API(middleware=self.middleware)
        self._add_routes(api)
        return api

    def _add_routes(self, api):
        api.add_route(ACQUISITION_PATH, self.acquisition_res)
        api.add_route(GET_REQUEST_PATH, self.request_management_res)
        api.add_route(DOWNLOAD_CALLBACK_PATH, self.download_callback_res)
        api.add_route(METADATA_PARSER_CALLBACK_PATH, self.metadata_callback_res)
        api.add_route(UPLOADER_REQUEST_PATH, self.uploader_res)



def get_app():
    """To be used by WSGI server."""
    configure_logging(logging.INFO)
    config = DasConfig.get_config()

    redis_client = redis.Redis(host=config.redis_host, port=config.redis_port,
                               password=config.redis_password, db=0)
    assert redis_client.ping()

    requests_store = AcquisitionRequestStore(redis_client)
    executor = ThreadPoolExecutor(4)

    auth_middleware = JwtMiddleware()
    auth_middleware.initialize(config.verification_key_url)

    return DasApi(requests_store, executor, config, auth_middleware).get_falcon_api()
