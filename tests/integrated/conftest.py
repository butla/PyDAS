import json
import os
import sys
import time
import yaml

from bravado.client import SwaggerClient
import docker
from mountepy import Mountebank, HttpService
import port_for
import pytest
import redis
import redis.connection

import tests
from tests.consts import (RSA_2048_PUB_KEY, TEST_VCAP_APPLICATION, TEST_VCAP_SERVICES_TEMPLATE,
                          TEST_AUTH_HEADER, TEST_ORG_UUID)
from data_acquisition.consts import DOWNLOADER_PATH, METADATA_PARSER_PATH
from data_acquisition.acquisition_request import AcquisitionRequestStore


REDIS_REPO = 'redis'
REDIS_IMAGE_TAG = '2.8.22'
REDIS_IMAGE = '{}:{}'.format(REDIS_REPO, REDIS_IMAGE_TAG)
DEFAULT_REDIS_PORT = 6379

DOWNLOADER_STUB_PORT = port_for.select_random()
METADATAPARSER_STUB_PORT = port_for.select_random()
USER_MANAGEMENT_STUB_PORT = port_for.select_random()
UAA_STUB_PORT = port_for.select_random()


def download_image_if_missing(docker_client):
    redis_images = docker_client.images(name=REDIS_REPO)
    proper_image_exists = bool([image for image in redis_images if REDIS_IMAGE in image['RepoTags']])
    if not proper_image_exists:
        print("Docker image {}:{} doesn't exist, trying to download... This may take a few minutes.")
        docker_client.pull(repository=REDIS_REPO, tag=REDIS_IMAGE_TAG)


def start_redis_container(docker_client):
    def wait_for_redis(port, timeout=5.0):
        start_time = time.perf_counter()
        redis_client = redis.Redis(port=port, db=0)
        while True:
            try:
                redis_client.ping()
                break
            except redis.connection.ConnectionError:
                time.sleep(0.01)
                if time.perf_counter() - start_time >= timeout:
                    raise TimeoutError('Waited too long for Redis to start accepting connections.')
    redis_port = port_for.select_random()
    host_config = docker_client.create_host_config(port_bindings={
        DEFAULT_REDIS_PORT: redis_port,
    })
    container_id = docker_client.create_container(REDIS_IMAGE, host_config=host_config)['Id']

    docker_client.start(container_id)
    wait_for_redis(redis_port)
    return container_id, redis_port


@pytest.yield_fixture(scope='session')
def redis_port():
    """
    Fixture that creates a Docker container with Redis for the whole test session.
    :return: Localhost's port on which Redis will listen.
    :rtype: int
    """
    # TODO add a clear message about Docker installation, if it isn't found
    # TODO also warn about configuring a proxy in /etc/config/docker
    docker_client = docker.Client(version='auto')
    download_image_if_missing(docker_client)
    container_id, redis_port = start_redis_container(docker_client)
    yield redis_port
    docker_client.remove_container(container_id, force=True)


@pytest.fixture(scope='session')
def redis_client_session(redis_port):
    return redis.Redis(port=redis_port, db=0)


@pytest.yield_fixture(scope='function')
def redis_client(redis_client_session):
    yield redis_client_session
    redis_client_session.flushdb()


@pytest.fixture(scope='function')
def req_store_real(redis_client):
    return AcquisitionRequestStore(redis_client)


@pytest.yield_fixture(scope='session')
def mountebank():
    mb = Mountebank()
    mb.start()
    yield mb
    mb.stop()


@pytest.yield_fixture(scope='function')
def downloader_imposter(mountebank):
    imposter = mountebank.add_imposter_simple(
        port=DOWNLOADER_STUB_PORT,
        path=DOWNLOADER_PATH,
        method='POST')
    yield imposter
    imposter.destroy()


@pytest.yield_fixture(scope='function')
def metadata_parser_imposter(mountebank):
    imposter = mountebank.add_imposter_simple(
        port=METADATAPARSER_STUB_PORT,
        path=METADATA_PARSER_PATH,
        method='POST')
    yield imposter
    imposter.destroy()


@pytest.yield_fixture(scope='function')
def user_management_imposter(mountebank):
    imposter_cfg = {
        'port': USER_MANAGEMENT_STUB_PORT,
        'protocol': 'http',
        'stubs': [
            {
                'responses': [
                    {
                        'is': {
                            'statusCode': 200,
                            'headers': {
                                'Content-Type': 'application/json'
                            },
                            'body': json.dumps([
                                {'organization': {'metadata': {'guid': TEST_ORG_UUID}}}
                            ]),
                        }
                    }
                ],
                'predicates': [
                    {
                        'and': [
                            {
                                'equals': {
                                    'path': '/rest/orgs/permissions',
                                    'method': 'GET',
                                },
                                'contains': {
                                    'headers': {
                                        'Authorization': TEST_AUTH_HEADER
                                    }
                                }
                            },
                        ]
                    }
                ]
            }
        ]
    }
    imposter = mountebank.add_imposter(imposter_cfg)
    yield imposter
    imposter.destroy()


@pytest.yield_fixture(scope='session')
def uaa_imposter(mountebank):
    imposter = mountebank.add_imposter_simple(
        port=UAA_STUB_PORT,
        method='GET',
        response=json.dumps({'value': RSA_2048_PUB_KEY}))
    yield imposter
    imposter.destroy()


@pytest.fixture(scope='session')
def vcap_services(redis_port):
    return TEST_VCAP_SERVICES_TEMPLATE.format(
        redis_port=redis_port,
        redis_password="null",
        redis_host='localhost',
        downloader_host='localhost:{}'.format(DOWNLOADER_STUB_PORT),
        metadata_parser_host='localhost:{}'.format(METADATAPARSER_STUB_PORT),
        user_management_host='localhost:{}'.format(USER_MANAGEMENT_STUB_PORT),
        verification_key_url='http://localhost:{}'.format(UAA_STUB_PORT)
    )


@pytest.yield_fixture(scope='session')
def das_session(vcap_services, uaa_imposter):
    waitress_path = os.path.join(os.path.dirname(sys.executable), 'waitress-serve')
    das_command = [
        waitress_path,
        '--port', '{port}',
        '--call', 'data_acquisition.app:get_app']

    project_root_path = os.path.join(waitress_path, '../../../..')
    das_service = HttpService(
        das_command,
        env={
            'VCAP_APPLICATION': TEST_VCAP_APPLICATION,
            'VCAP_SERVICES': vcap_services,
            'VCAP_APP_PORT': '{port}',
            'PYTHONPATH': project_root_path})

    das_service.start()
    yield das_service
    das_service.stop()


@pytest.fixture(scope='function')
def das(das_session,
        downloader_imposter,
        metadata_parser_imposter,
        user_management_imposter):
    return das_session


@pytest.fixture(scope='session')
def swagger_spec(das_session):
    spec_file_path = os.path.join(tests.__path__[0], '../api_doc.yaml')
    with open(spec_file_path) as spec_file:
        return yaml.load(spec_file)


@pytest.fixture
def das_client(das, swagger_spec):
    return SwaggerClient.from_spec(swagger_spec, origin_url=das.url)
