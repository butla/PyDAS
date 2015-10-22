"""
Application for downloading data sets from the web.
This file is used to create the WSGI app that can be embedded in a container.
"""

import logging
import multiprocessing
import os
from urllib.parse import urljoin

import falcon
import redis
import rq

from .cf_app_utils.auth.falcon_middleware import JwtMiddleware
from .cf_app_utils import configure_logging
from .consts import ACQUISITION_PATH, DOWNLOADER_PATH
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

    # config part
    downloader_url = urljoin(os.environ['DOWNLOADER_URL'], DOWNLOADER_PATH)
    redis_port = int(os.environ['REDIS_PORT'])
    public_key_url = os.environ['PUBLIC_KEY_URL']

    auth_middleware = JwtMiddleware(public_key_url)
    auth_middleware.initialize()

    requests_store = redis.Redis(port=redis_port, db=0)
    queue = rq.Queue(connection=redis.Redis(port=redis_port, db=1))

    application = falcon.API(middleware=auth_middleware)
    application.add_route(
        ACQUISITION_PATH,
        AcquisitionRequestsResource(requests_store, queue, downloader_url))

    start_queue_worker(queue)
    return application
