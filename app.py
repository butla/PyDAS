__author__ = 'butla'

import multiprocessing
import falcon
import json
import os
import requests
import logging
import time
import redis
import rq


def fake_work():
    for i in range(5):
        print(i)
        time.sleep(1)


class SampleResource:
    @staticmethod
    def on_get(req, resp):
        resp.body = 'Hello world\n'
        logging.info('info')
        logging.error('error')


    @staticmethod
    def on_post(req, resp):
        '''
        Given JSON input returns a JSON with only the keys that start with "A" (case insensitive).
        '''
        if req.content_type != 'application/json':
            raise falcon.HTTPUnsupportedMediaType('Media type needs to be application/json')
        body_json = json.loads(req.stream.read().decode('utf-8'))

        queue.enqueue(fake_work)
        # resp.body = json.dumps({key: value for key, value in body_json.items() if key.lower().startswith('a')})

application = falcon.API()
application.add_route('/', SampleResource())

redis_port = int(os.environ['REDIS_PORT'])
queue = rq.Queue(connection=redis.Redis(port=redis_port))


def start_queue_worker():
    def do_work():
        # TODO put this in a loop with catching exceptions
        with rq.Connection(queue.connection):
            rq.Worker(queue).work()

    # Moze jednak workery na calkiem osobnym procesie w innym pliku? zeby startowały niezaleznie od gunicorna
    # Albo jakos owinac metode api, zeby, jak leci pierwsze rzadanie na danym procesie to sie tworzyl worker.
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
