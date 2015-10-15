import json
import sys

import os
import requests
import redis
from mountepy import HttpService

from data_acquisition.consts import DOWNLOAD_CALLBACK_PATH
from .consts import RSA_2048_PUB_KEY, TEST_AUTH_HEADER, TEST_DOWNLOAD_REQUEST
from .utils import dict_is_part_of


# @pytest.fixture(scope='function')
# def das(request):
#     def fin():
#         mountebank_global.reset()
#     das_service =
#     request.addfinalizer(fin)
#     return mountebank_global


# TODO add imposter calling_url field (other url should be management_url)
def test_service_start(mountebank, redis_port):
    downloader_imposter = mountebank.add_imposter_simple(method='POST')
    uaa_imposter = mountebank.add_imposter_simple(
        method='GET',
        response=json.dumps({'value': RSA_2048_PUB_KEY}))

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
            'VCAP_APP_PORT': '{port}'
        })

    with das:
        response = requests.post(
            'http://localhost:{}'.format(das.port),
            json=TEST_DOWNLOAD_REQUEST,
            headers={'Authorization': TEST_AUTH_HEADER}
        )

        assert response.status_code == 202
        req_store_id = '{}:{}'.format(TEST_DOWNLOAD_REQUEST['orgUUID'], response.json()['id'])
        redis_client = redis.Redis(port=redis_port, db=0)
        assert redis_client.get(req_store_id)

        request_to_imposter = downloader_imposter.wait_for_requests()[0]
        assert json.loads(request_to_imposter.body) == {
            'source': TEST_DOWNLOAD_REQUEST['source'],
            'callback': 'http://localhost:{}{}'.format(das.port, DOWNLOAD_CALLBACK_PATH)
        }
        assert dict_is_part_of(request_to_imposter.headers, {'authorization': TEST_AUTH_HEADER})
