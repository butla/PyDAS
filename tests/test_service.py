import json
import os
import sys

import requests

from mountepy import HttpService


def _is_part_of(dict_a, dict_b):
    """
    Checks whether dict_b is a part of dict_a.
    That is if dict_b is dict_a, just with some keys removed.
    :param dict dict_a:
    :param dict dict_b:
    :rtype: bool
    """
    for key, value in dict_b.items():
        if key not in dict_a or dict_a[key] != value:
            return False
    return True


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

        request_to_imposter = imposter.wait_for_requests()[0]
        assert json.loads(request_to_imposter.body) == {'something': 'yeah, not much'}
        # TODO actually validate JWT token
        assert _is_part_of(request_to_imposter.headers, {'authorization': 'bearer blablabla'})
