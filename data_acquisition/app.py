"""
Application for downloading data sets from the web.
This file is used to create the WSGI app that can be embedded in a container.
"""

import logging
import multiprocessing
import signal
import sys

import falcon
import redis
import rq

from .cf_app_utils.auth.falcon import JwtMiddleware
from .cf_app_utils import configure_logging
from .config import DasConfig
from .consts import (ACQUISITION_PATH, DOWNLOAD_CALLBACK_PATH, UPLOADER_REQUEST_PATH,
                     METADATA_PARSER_CALLBACK_PATH, GET_REQUEST_PATH)
from .acquisition_request import AcquisitionRequestStore
from .resources import (AcquisitionRequestsResource, SingleAcquisitionRequestResource,
                        DownloadCallbackResource, UploaderResource, MetadataCallbackResource)


def start_queue_worker(queue):
    """
    Starts a process processing requests put into the Redis queue.
    """
    def do_work():
        """
        Function that actually consumes the tasks from queue.
        """
        with rq.Connection(queue.connection):
            rq.Worker(queue, default_result_ttl=0).work()

    def terminate_handler(signo, stack_frame):
        """
        Stops Redis queue worker process when this process receives the terminate signal.
        """
        queue_worker.terminate()
        sys.exit(0)

    logging.info('starting queue worker process')
    queue_worker = multiprocessing.Process(target=do_work)
    signal.signal(signal.SIGTERM, terminate_handler)
    queue_worker.start()


def add_resources_to_routes(application, requests_store, queue, config):
    """
    Creates REST resources for the application and puts them on proper paths.
    :param `falcon.API` application: A Falcon application.
    :param `.acquisition_request.AcquisitionRequestStore` req_store:
    :param `rq.Queue` queue:
    :param `data_acquisition.DasConfig` config: Configuration object for the application.
    """
    application.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(requests_store, queue, config))
    application.add_route(
        GET_REQUEST_PATH,
        SingleAcquisitionRequestResource(requests_store))
    application.add_route(
        DOWNLOAD_CALLBACK_PATH,
        DownloadCallbackResource(requests_store, queue, config))
    application.add_route(
        UPLOADER_REQUEST_PATH,
        UploaderResource(requests_store, queue, config))
    application.add_route(
        METADATA_PARSER_CALLBACK_PATH,
        MetadataCallbackResource(requests_store, config))


def get_app():
    """
    To be used by WSGI server.
    """
    configure_logging(logging.INFO)

    config = DasConfig.get_config()

    auth_middleware = JwtMiddleware()
    auth_middleware.initialize(config.verification_key_url)

    requests_store = AcquisitionRequestStore(redis.Redis(
        port=config.redis_port,
        password=config.redis_password,
        db=0))
    queue = rq.Queue(connection=redis.Redis(
        host=config.redis_host,
        port=config.redis_port,
        password=config.redis_password,
        db=1))

    application = falcon.API(middleware=auth_middleware)
    add_resources_to_routes(application, requests_store, queue, config)

    start_queue_worker(queue)
    return application
