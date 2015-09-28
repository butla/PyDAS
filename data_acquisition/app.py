__author__ = 'butla'

import multiprocessing
import falcon
import os
import requests
import logging
import redis
import rq

# config part
DOWNLOADER_URL = os.environ['DOWNLOADER_URL']
REDIS_PORT = int(os.environ['REDIS_PORT'])


class SampleResource:

    @staticmethod
    def on_get(req, resp):
        resp.body = 'Hello world\n'

    @staticmethod
    def on_post(req, resp):
        #body_json = json.loads(req.stream.read().decode('utf-8'))
        queue.enqueue(requests.post, DOWNLOADER_URL, json={'something': 'yeah, not much'})

application = falcon.API()
application.add_route('/', SampleResource())

queue = rq.Queue(connection=redis.Redis(port=REDIS_PORT))


def start_queue_worker():
    def do_work():
        # TODO put this in a loop with catching exceptions
        with rq.Connection(queue.connection):
            rq.Worker(queue).work()

    logging.info('starting queue worker process')
    queue_worker = multiprocessing.Process(target=do_work)
    queue_worker.start()


def get_app():
    """
    To be used by WSGI server.
    """
    logging.basicConfig(level=logging.INFO)
    start_queue_worker()
    return application
