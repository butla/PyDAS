"""
REST resources of the app.
"""

import json
import logging
from urllib.parse import urljoin

import requests
from cerberus import Validator
import falcon

from .consts import DOWNLOAD_CALLBACK_PATH
from .requests import AcquisitionRequest


class AcquisitionRequestsResource:

    """
    Resource governing data acquisition (download) requests.
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
        self._download_req_validator = Validator(schema={
            'category': {'type': 'string', 'required': True},
            'orgUUID': {'type': 'string', 'required': True},
            'publicRequest': {'type': 'boolean', 'required': True},
            'source': {'type': 'string', 'required': True},
            'title': {'type': 'string', 'required': True},
        })

    def on_post(self, req, resp):
        """
        Requesting a new data set download.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        """
        acquisition_req = self._get_acquisition_req(req)
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
        return AcquisitionRequest(**req_json)

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
            json=self._get_download_req(acquisition_req),
            headers={'Authorization': req_auth})

    def _get_download_req(self, acquisition_req):
        return {
            'source': acquisition_req.source,
            'callback': urljoin(
                self._config.self_url,
                DOWNLOAD_CALLBACK_PATH.format(acquisition_req.id))
        }
