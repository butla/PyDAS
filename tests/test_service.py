import docker
import docker.utils
import os
import port_for
import requests
import sys

from mountepy import HttpService, wait_for_port

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
    host_config = docker.utils.create_host_config(port_bindings={
        DEFAULT_REDIS_PORT: redis_port,
    })
    container_id = docker_client.create_container(REDIS_IMAGE, host_config=host_config)['Id']

    docker_client.start(container_id)
    wait_for_port(redis_port)
    return container_id, redis_port


def test_service_start():
    docker_client = docker.Client(version='auto')
    download_image_if_missing(docker_client)
    container_id, redis_port = start_redis_container(docker_client)

    try:
        app_port = port_for.select_random()
        gunicorn_path = os.path.join(os.path.dirname(sys.executable), 'gunicorn')

        das_command = [
            gunicorn_path,
            'data_acquisition.app:get_app()',
            '--bind', ':{port}',
            '--enable-stdio-inheritance',
            '--pythonpath', ','.join(sys.path)]
        das = HttpService(
            das_command,
            port=app_port,
            env={
                'REDIS_PORT': str(redis_port),
                'DOWNLOADER_URL': 'http://localhost:2525'
            })

        with das:
            assert requests.post('http://localhost:{}'.format(app_port)).status_code == 200
            import time
            time.sleep(3)
            # TODO create mock edpoints and assert that they were called
    finally:
        docker_client.remove_container(container_id, force=True)