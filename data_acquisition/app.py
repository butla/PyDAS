__author__ = 'butla'

import multiprocessing
import falcon
import os
import requests
import logging
import redis
import rq

import cf_app_utils.auth.falcon as falcon_cf


class SampleResource:

    def __init__(self, queue, downloader_url):
        """
        :param queue: object compatible with `rq.Queue` interface
        :param str downloader_url:
        """
        self._queue = queue
        self._downloader_url = downloader_url

    @staticmethod
    def on_get(req, resp):
        resp.body = 'Hello world\n'

    def on_post(self, req, resp):
        #body_json = json.loads(req.stream.read().decode('utf-8'))
        token = req.auth
        self._queue.enqueue(requests.post,
                      url=self._downloader_url,
                      json={'something': 'yeah, not much'},
                      headers={'Authorization': token})


def start_queue_worker(queue):
    def do_work():
        # TODO put this in a loop with catching exceptions
        with rq.Connection(queue.connection):
            rq.Worker(queue).work()

    logging.info('starting queue worker process')
    queue_worker = multiprocessing.Process(target=do_work)
    queue_worker.start()


# TODO exclude from coverage tools, because it can't be covered traditionally
def get_app():
    """
    To be used by WSGI server.
    """
    logging.basicConfig(level=logging.INFO)

    # config part
    downloader_url = os.environ['DOWNLOADER_URL']
    redis_port = int(os.environ['REDIS_PORT'])
    public_key_url = os.environ['PUBLIC_KEY_URL']

    auth_middleware = falcon_cf.JwtMiddleware(public_key_url)
    auth_middleware.initialize()

    queue = rq.Queue(connection=redis.Redis(port=redis_port))

    application = falcon.API(middleware=auth_middleware)
    application.add_route('/', SampleResource(queue, downloader_url))

    start_queue_worker(queue)
    return application
