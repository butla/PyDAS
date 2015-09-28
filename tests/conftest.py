import docker
import port_for

import pytest

from mountepy import Mountebank, wait_for_port

REDIS_REPO = 'redis'
REDIS_IMAGE_TAG = '2.8.22'
REDIS_IMAGE = '{}:{}'.format(REDIS_REPO, REDIS_IMAGE_TAG)
DEFAULT_REDIS_PORT = 6379


def download_image_if_missing(docker_client):
    redis_images = docker_client.images(name=REDIS_REPO)
    proper_image_exists = bool([image for image in redis_images if REDIS_IMAGE in image['RepoTags']])
    if not proper_image_exists:
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