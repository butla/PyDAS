import json
import os
import sys

import requests

from mountepy import HttpService


def test_service_start(mountebank, redis_port):
    imposter = mountebank.add_imposter_simple(method='POST')

    gunicorn_path = os.path.join(os.path.dirname(sys.executable), 'gunicorn')
    das_command = [
        gunicorn_path,
        'data_acquisition.app:get_app()',
        '--bind', ':{port}',
        '--enable-stdio-inheritance',
        '--pythonpath', ','.join(sys.path)]

    das = HttpService(
        das_command,
        env={
            'REDIS_PORT': str(redis_port),
            'DOWNLOADER_URL': 'http://localhost:{}'.format(imposter.port)
        })

    with das:
        assert requests.post('http://localhost:{}'.format(das.port)).status_code == 200
        assert json.loads(imposter.wait_for_requests()[0].body) == {'something': 'yeah, not much'}
