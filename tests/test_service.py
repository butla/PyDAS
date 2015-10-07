import json
import os
import sys

import jwt
import requests

from mountepy import HttpService
from .consts import RSA_2048_PRIV_KEY, RSA_2048_PUB_KEY


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
    downloader_imposter = mountebank.add_imposter_simple(method='POST')
    uaa_imposter = mountebank.add_imposter_simple(method='GET', response=json.dumps({'value': RSA_2048_PUB_KEY}))
    # TODO add imposter calling_url field (other url should be management_url)

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
            'DOWNLOADER_URL': 'http://localhost:{}'.format(downloader_imposter.port),
            'PUBLIC_KEY_URL': 'http://localhost:{}'.format(uaa_imposter.port),
        })

    with das:
        test_token = jwt.encode(payload={'a': 'b'}, key=RSA_2048_PRIV_KEY, algorithm='RS256').decode()
        response = requests.post(
            'http://localhost:{}'.format(das.port),
            headers={'Authorization': 'bearer {}'.format(test_token)}
        )

        assert response.status_code == 200
        request_to_imposter = downloader_imposter.wait_for_requests()[0]
        assert json.loads(request_to_imposter.body) == {'something': 'yeah, not much'}
        assert _is_part_of(request_to_imposter.headers, {'authorization': 'bearer {}'.format(test_token)})

# TODO add bad signature test
