from unittest.mock import MagicMock
import os

from bravado.client import SwaggerClient
import yaml

import tests
from tests.consts import TEST_DOWNLOAD_REQUEST
from tests.utils import FalconTestHttpClient

# TODO this is just a test to check if bravado integration is working
def test_acquisition_request_with_swagger(falcon_api, monkeypatch):
    # arrange
    # we need to cut out the access validation method
    # TODO this needs to be refactored. There needs to be a way to supply custom resource objects.
    monkeypatch.setattr(
        'data_acquisition.cf_app_utils.auth.falcon.FalconUserOrgAccessChecker.validate_access',
        MagicMock())

    spec_file_path = os.path.join(tests.__path__[0], '../api_doc.yaml')
    with open(spec_file_path) as spec_file:
        swagger_spec = yaml.load(spec_file)

    client = SwaggerClient.from_spec(swagger_spec, http_client=FalconTestHttpClient(falcon_api))

    SwaggerAcquisitionRequest = client.get_model('AcquisitionRequest')
    request_body = SwaggerAcquisitionRequest(**TEST_DOWNLOAD_REQUEST)

    # act
    resp_object = client.rest.submitAcquisitionRequest(body=request_body).result()

    # assert
    assert resp_object