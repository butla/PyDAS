"""
REST resources of the app.
"""

import json
import logging
import os
import requests
from urllib.parse import urljoin
import uuid

from cerberus import Validator
import falcon

from .consts import DOWNLOADER_PATH, DOWNLOAD_CALLBACK_PATH


class AcquisitionRequestsResource:

    """
    Resource governing data acquisition (download) requests.
    """

    def __init__(self, req_store, queue, downloader_url):
        """
        :param `redis.Redis` req_store: client for download requests' DB
        :param `rq.Queue` queue:
        :param str downloader_url: URL on which download request should be sent
        """
        self._req_store = req_store
        self._queue = queue
        self._downloader_url = downloader_url
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
        self._req_store.set(acquisition_req.get_store_key(), str(acquisition_req))
        self._enqueue_downloader_request(acquisition_req, req.auth)

        resp.body = str(acquisition_req)
        resp.status = falcon.HTTP_ACCEPTED

    def _get_acquisition_req(self, req):
        """
        :param `falcon.Request` req:
        :returns: A parsed acquisition request sent to the service.
        :rtype: AcquisitionRequest
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
        self._queue.enqueue(
            requests.post,
            url=self._downloader_url,
            json=self._get_download_req(acquisition_req),
            headers={'Authorization': req_auth})

    @staticmethod
    def _get_download_req(acquisition_req):
        # TODO take port and uri from some config which should be created from environment variables
        app_port = os.environ['VCAP_APP_PORT']
        return {
            'source': acquisition_req.source,
            'callback': 'http://localhost:{}{}'.format(app_port, DOWNLOAD_CALLBACK_PATH)
        }


class AcquisitionRequest:

    """
    Data set download request.
    """

    def __init__(
            self,
            orgUUID,
            publicRequest,
            source,
            category,
            title,
            status='VALIDATED',
            id=None):
        self.orgUUID = orgUUID
        self.publicRequest = publicRequest
        self.source = source
        self.category = category
        self.title = title
        self.status = status
        # TODO maybe a creation time is needed
        if id:
            self.id = id
        else:
            self.id = str(uuid.uuid4())

    def __str__(self):
        return json.dumps(self.__dict__)

    def get_store_key(self):
        return '{}:{}'.format(self.orgUUID, self.id)
