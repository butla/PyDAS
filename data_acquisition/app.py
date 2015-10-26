"""
Application for downloading data sets from the web.
This file is used to create the WSGI app that can be embedded in a container.
"""

import logging
import multiprocessing

import falcon
import redis
import rq

from .cf_app_utils.auth.falcon_middleware import JwtMiddleware
from .cf_app_utils import configure_logging
from .config import DasConfig
from .consts import ACQUISITION_PATH
from .resources import AcquisitionRequestsResource


def start_queue_worker(queue):
    """
    Starts a process processing requests put into the Redis queue.
    """
    def do_work():
        """
        Function that actually consumes the tasks from queue.
        """
        # TODO put this in a loop with catching exceptions
        # TODO add a test for caching the exception and maybe put this in another file
        with rq.Connection(queue.connection):
            rq.Worker(queue).work()

    logging.info('starting queue worker process')
    queue_worker = multiprocessing.Process(target=do_work)
    queue_worker.start()


def get_app():
    """
    To be used by WSGI server.
    """
    configure_logging(logging.INFO)

    config = DasConfig.get_config()

    auth_middleware = JwtMiddleware(config.verification_key_url)
    auth_middleware.initialize()

    requests_store = redis.Redis(
        port=config.redis_port,
        password=config.redis_password,
        db=0)
    queue = rq.Queue(connection=redis.Redis(
        port=config.redis_port,
        password=config.redis_password,
        db=1))

    application = falcon.API(middleware=auth_middleware)
    application.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(requests_store, queue, config))

    start_queue_worker(queue)
    return application
