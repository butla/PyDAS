from unittest.mock import MagicMock
import os

from bravado.client import SwaggerClient
import yaml

import tests
from tests.consts import TEST_DOWNLOAD_REQUEST
from tests.falcon_bravado import FalconTestHttpClient


# TODO test bravado integration in isolation from PyDAS's resources
def test_acquisition_request_with_swagger(das_api):
    # arrange
    das_api.acquisition_res._org_checker = MagicMock()

    spec_file_path = os.path.join(tests.__path__[0], '../api_doc.yaml')
    with open(spec_file_path) as spec_file:
        swagger_spec = yaml.load(spec_file)

    client = SwaggerClient.from_spec(swagger_spec,
                                     http_client=FalconTestHttpClient(das_api.api))

    SwaggerAcquisitionRequest = client.get_model('AcquisitionRequest')
    request_body = SwaggerAcquisitionRequest(**TEST_DOWNLOAD_REQUEST)

    # act
    resp_object = client.rest.submitAcquisitionRequest(body=request_body).result()

    # assert
    assert resp_object