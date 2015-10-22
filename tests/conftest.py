import json
import os
import sys

import docker
from mountepy import Mountebank, HttpService, wait_for_port
import port_for
import pytest

from .consts import RSA_2048_PUB_KEY
from data_acquisition.consts import DOWNLOADER_PATH


REDIS_REPO = 'redis'
REDIS_IMAGE_TAG = '2.8.22'
REDIS_IMAGE = '{}:{}'.format(REDIS_REPO, REDIS_IMAGE_TAG)
DEFAULT_REDIS_PORT = 6379


def download_image_if_missing(docker_client):
    redis_images = docker_client.images(name=REDIS_REPO)
    proper_image_exists = bool([image for image in redis_images if REDIS_IMAGE in image['RepoTags']])
    if not proper_image_exists:
        print("Docker image {}:{} doesn't exist, trying to download... This may take a few minutes.")
        docker_client.pull(repository=REDIS_REPO, tag=REDIS_IMAGE_TAG)


def start_redis_container(docker_client):
    redis_port = port_for.select_random()
    host_config = docker_client.create_host_config(port_bindings={
        DEFAULT_REDIS_PORT: redis_port,
    })
    container_id = docker_client.create_container(REDIS_IMAGE, host_config=host_config)['Id']

    docker_client.start(container_id)
    wait_for_port(redis_port)
    return container_id, redis_port


@pytest.fixture(scope='session')
def redis_port(request):
    """
    Fixture that creates a Docker container with Redis for the whole test session.
    :return: Localhost's port on which Redis will listen.
    :rtype: int
    """
    def fin():
        docker_client.remove_container(container_id, force=True)
    request.addfinalizer(fin)

    # TODO add a clear message about Docker installation, if it isn't found
    # TODO alsa warn about configuring a proxy in /etc/config/docker
    docker_client = docker.Client(version='auto')
    download_image_if_missing(docker_client)
    container_id, redis_port = start_redis_container(docker_client)
    return redis_port


@pytest.fixture(scope='session')
def mountebank_global(request):
    def fin():
        mb.stop()
    request.addfinalizer(fin)

    mb = Mountebank()
    mb.start()
    return mb


@pytest.fixture(scope='function')
def mountebank(request, mountebank_global):
    def fin():
        mountebank_global.reset()
    request.addfinalizer(fin)
    return mountebank_global


@pytest.fixture(scope='function')
def downloader_imposter(mountebank):
    return mountebank.add_imposter_simple(path=DOWNLOADER_PATH, method='POST')


@pytest.fixture(scope='function')
def uaa_imposter(mountebank):
    return mountebank.add_imposter_simple(
        method='GET',
        response=json.dumps({'value': RSA_2048_PUB_KEY}))


@pytest.fixture(scope='function')
def das(request, redis_port, downloader_imposter, uaa_imposter):
    def fin():
        das_service.stop()
    request.addfinalizer(fin)

    gunicorn_path = os.path.join(os.path.dirname(sys.executable), 'gunicorn')
    das_command = [
        gunicorn_path,
        'data_acquisition.app:get_app()',
        '--bind', ':{port}',
        '--enable-stdio-inheritance',
        '--pythonpath', ','.join(sys.path)]

    das_service = HttpService(
        das_command,
        env={
            'REDIS_PORT': str(redis_port),
            'DOWNLOADER_URL': 'http://localhost:{}'.format(downloader_imposter.port),
            'PUBLIC_KEY_URL': 'http://localhost:{}'.format(uaa_imposter.port),
            'VCAP_APP_PORT': '{port}'
        })

    das_service.start()
    return das_service