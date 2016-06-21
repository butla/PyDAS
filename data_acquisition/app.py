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
from .resources import (AcquisitionRequestsResource, SingleAcquisitionRequestResource,
                        DownloadCallbackResource, UploaderResource, MetadataCallbackResource)


def add_resources_to_routes(application, requests_store, executor, config):
    """
    Creates REST resources for the application and puts them on proper paths.
    :param `falcon.API` application: A Falcon application.
    :param `.acquisition_request.AcquisitionRequestStore` req_store:
    :param `concurrent.futures.Executor` executor: Object that will run background jobs for the
        application.
    :param `data_acquisition.DasConfig` config: Configuration object for the application.
    """
    application.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(requests_store, executor, config))
    application.add_route(
        GET_REQUEST_PATH,
        SingleAcquisitionRequestResource(requests_store, config))
    application.add_route(
        DOWNLOAD_CALLBACK_PATH,
        DownloadCallbackResource(requests_store, executor, config))
    application.add_route(
        UPLOADER_REQUEST_PATH,
        UploaderResource(requests_store, executor, config))
    application.add_route(
        METADATA_PARSER_CALLBACK_PATH,
        MetadataCallbackResource(requests_store, config))


def get_app():
    """
    To be used by WSGI server.
    """
    configure_logging(logging.INFO)
    config = DasConfig.get_config()

    redis_client = redis.Redis(host=config.redis_host, port=config.redis_port,
                               password=config.redis_password, db=0)
    assert redis_client.ping()

    requests_store = AcquisitionRequestStore(redis_client)
    executor = ThreadPoolExecutor(4)

    auth_middleware = JwtMiddleware()
    auth_middleware.initialize(config.verification_key_url)

    application = falcon.API(middleware=auth_middleware)
    add_resources_to_routes(application, requests_store, executor, config)

    return application
