"""
REST resources of the app.
"""

import json
import logging
from urllib.parse import urljoin

from cerberus import Validator
import falcon
import requests

from .acquisition_request import AcquisitionRequest
from .consts import DOWNLOAD_CALLBACK_PATH, METADATA_PARSER_CALLBACK_PATH
from .cf_app_utils.auth.falcon import FalconUserOrgAccessChecker


def get_download_callback_url(das_url, req_id):
    """
    :param str req_id: acquisition request ID
    :return: The URL for file download callback for the given request.
    :rtype: str
    """
    return urljoin(das_url, DOWNLOAD_CALLBACK_PATH.format(req_id=req_id))


def get_metadata_callback_url(das_url, req_id):
    """
    :param str req_id: acquisition request ID
    :return: The URL for metadata parse callback for the given request.
    :rtype: str
    """
    return urljoin(das_url, METADATA_PARSER_CALLBACK_PATH.format(req_id=req_id))


class DasResource:

    """
    Base class for other of the app's resources.
    """

    def __init__(self, req_store, queue, config):
        """
        :param `.requests.AcquisitionRequestStore` req_store:
        :param `rq.Queue` queue:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        self._req_store = req_store
        self._queue = queue
        self._config = config
        self._log = logging.getLogger(type(self).__name__)

    def _get_download_callback_url(self, req_id):
        """
        :param str req_id: acquisition request ID
        :return: The URL for file download callback for the given request.
        :rtype: str
        """
        return get_download_callback_url(self._config.self_url, req_id)

    def _get_metadata_callback_url(self, req_id):
        """
        :param str req_id: acquisition request ID
        :return: The URL for metadata parse callback for the given request.
        :rtype: str
        """
        return get_metadata_callback_url(self._config.self_url, req_id)


class AcquisitionRequestsResource(DasResource):

    """
    Resource governing data acquisition (download) requests.
    """

    def __init__(self, req_store, queue, config):
        """
        :param `.requests.AcquisitionRequestStore` req_store:
        :param `rq.Queue` queue:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        super().__init__(req_store, queue, config)
        self._download_req_validator = Validator(schema={
            'category': {'type': 'string', 'required': True},
            'orgUUID': {'type': 'string', 'required': True},
            'publicRequest': {'type': 'boolean', 'required': True},
            'source': {'type': 'string', 'required': True},
            'title': {'type': 'string', 'required': True},
        })
        self._org_checker = FalconUserOrgAccessChecker(config.user_management_url)

    def on_post(self, req, resp):
        """
        Requesting a new data set download.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        """
        acquisition_req = self._get_acquisition_req(req)
        self._org_checker.validate_access(req.auth, [acquisition_req.orgUUID])

        self._req_store.put(acquisition_req)
        self._enqueue_downloader_request(acquisition_req, req.auth)

        resp.body = str(acquisition_req)
        resp.status = falcon.HTTP_ACCEPTED

    def _get_acquisition_req(self, req):
        """
        :param `falcon.Request` req:
        :returns: A parsed acquisition request sent to the service.
        :rtype: data_acquisition.requests.AcquisitionRequest
        :raises `falcon.HTTPBadRequest`: When the request is invalid.
        """
        req_json = json.loads(req.stream.read().decode())
        if not self._download_req_validator.validate(req_json):
            err_msg = 'Errors in download parameters: {}'.format(
                self._download_req_validator.errors)
            self._log.error(err_msg)
            raise falcon.HTTPBadRequest('Invalid parameters', err_msg)
        acquisition_req = AcquisitionRequest(**req_json)
        acquisition_req.set_validated()
        return acquisition_req

    def _enqueue_downloader_request(self, acquisition_req, req_auth):
        """
        Queues sending a request to Downloader.
        It will download the file specified in acquisition request
        and call a callback on this app.
        :param AcquisitionRequest acquisition_req:
        :param str req_auth: Value of Authorization header, the token.
        """
        # TODO there should be function with exception handling instead of just passing parameters
        self._queue.enqueue(
            requests.post,
            url=self._config.downloader_url,
            json={
                'source': acquisition_req.source,
                'callback': self._get_download_callback_url(acquisition_req.id)
            },
            headers={'Authorization': req_auth})


class DownloadCallbackResource(DasResource):

    """
    Resource accepting callbacks from the Downloader.
    """

    def __init__(self, req_store, queue, config):
        """
        :param `.requests.AcquisitionRequestStore` req_store:
        :param `rq.Queue` queue:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        super().__init__(req_store, queue, config)
        self._callback_validator = Validator(schema={
            'id': {'type': 'string', 'required': True},
            'state': {'type': 'string', 'required': True},
            'savedObjectId': {'type': 'string', 'required': True},
            'objectStoreId': {'type': 'string', 'required': True},
            })

    def on_post(self, req, resp, req_id):
        """
        Callback after download of the data set.
        This will trigger a request to Metadata Parser.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        :param str req_id: ID given to the original acquisition request
        """
        req_json = json.loads(req.stream.read().decode())
        if not self._callback_validator.validate(req_json):
            err_msg = 'Errors in download callback parameters: {}'.format(
                self._callback_validator.errors)
            self._log.error(err_msg)
            raise falcon.HTTPBadRequest('Invalid parameters', err_msg)

        acquisition_req = self._req_store.get(req_id)
        if req_json['state'] == 'DONE':
            acquisition_req.set_downloaded()
            self._req_store.put(acquisition_req)
            self._enqueue_metadata_request(acquisition_req, req_json, req.auth)
        else:
            acquisition_req.set_error()
            self._req_store.put(acquisition_req)

    def _enqueue_metadata_request(self, acquisition_req, download_callback, req_auth):
        """
        Queues sending a request to Metadata Parser.
        It will extract metadata from the downloaded file, make sure it gets indexed
        and call a callback on this app.
        :param AcquisitionRequest acquisition_req: The original acquisition request.
        :param dict download_callback: Callback request gotten from Downloader.
        :param str req_auth: Value of Authorization header, the token.
        """
        metadata_parse_req = {
            'orgUUID': acquisition_req.orgUUID,
            'publicRequest': acquisition_req.publicRequest,
            'source': acquisition_req.source,
            'category': acquisition_req.category,
            'title': acquisition_req.title,
            'id': acquisition_req.id,
            'idInObjectStore': download_callback['objectStoreId'],
            'callbackUrl': self._get_metadata_callback_url(acquisition_req.id)
        }

        # TODO there should be function with exception handling instead of just passing parameters
        self._queue.enqueue(
            requests.post,
            url=self._config.metadata_parser_url,
            json=metadata_parse_req,
            headers={'Authorization': req_auth})
