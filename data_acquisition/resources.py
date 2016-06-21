"""
REST resources of the app.
"""

import itertools
import json
import logging
from urllib.parse import urljoin

from cerberus import Validator
import falcon
import requests

from .acquisition_request import AcquisitionRequest, RequestNotFoundError
from .consts import DOWNLOAD_CALLBACK_PATH, METADATA_PARSER_CALLBACK_PATH
from .cf_app_utils.auth.falcon import FalconUserOrgAccessChecker

LOG = logging.getLogger(__name__)


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


class SecretString:

    """
    A wrapper for a string that makes it not visible in the logs.
    """

    def __init__(self, string):
        self.string = string

    def __repr__(self):
        return 'SecretString()'

    def __eq__(self, other):
        return self.value() == other.value()

    def value(self):
        """
        Get the value of the string wrapped by this object.
        """
        return self.string


def external_service_call(url, data, hidden_token):
    """
    Sends a request to an external service.
    When passing this function to Redis queue the user's token isn't logged.
    :param str url: URL for the call.
    :param dict data: The data to be sent.
    :param `SecretString` hidden_token: Wrapped user's OAuth token.
    :returns: True when request succeeds, false otherwise.
    :rtype: bool
    """
    try:
        resp = requests.post(url, json=data, headers={'Authorization': hidden_token.value()})
        if resp.ok:
            LOG.info('Successful request to %s with data %s', url, data)
            return True
        else:
            LOG.error(
                'Request failed:\nURL: %s\ndata: %s\nservice response:%s',
                url,
                data,
                resp.text
            )
    except requests.exceptions.ConnectionError:
        LOG.exception('Error when sending a request to %s with data %s', url, data)
    return False


class DasResource:

    """
    Base class for other of the app's resources.
    """

    def __init__(self, req_store, executor, config):
        """
        :param `data_acquisition.acquisition_request.AcquisitionRequestStore` req_store:
        :param `concurrent.futures.ThreadPoolExecutor` executor: Responsible for asynchronous
            sending of messages to other services.
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        self._req_store = req_store
        self._executor = executor
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

    def _parse_request(self, req, validator, operation_name):
        """
        Parses and validates the body of a request.
        :param `falcon.Request` req:
        :param `cerberus.Validator` validator: Validator for the request.
        :param operation_name: Name for the operation being performed on the request.
        :return: Validated body of the request as JSON.
        :rtype: dict
        :raises `falcon.HTTPBadRequest`: When the parameters are invalid.
        """
        req_json = json.loads(req.stream.read().decode())
        if not validator.validate(req_json):
            err_msg = 'Errors in {} parameters: {}'.format(operation_name, validator.errors)
            self._log.error(err_msg)
            raise falcon.HTTPBadRequest('Invalid parameters', err_msg)
        return req_json

    def _enqueue_metadata_request(self, acquisition_req, id_in_object_store, req_auth):
        """
        Queues sending a request to Metadata Parser.
        It will extract metadata from the downloaded file, make sure it gets indexed
        and call a callback on this app.
        :param AcquisitionRequest acquisition_req: The original acquisition request.
        :param str id_in_object_store: Identifier for the dataset in a service storing it.
        If not set, then the request will be sent without it.
        This must only occur when "source" is an HDFS URI.
        Metadata Parser will extract the value by itself from URI.
        :param str req_auth: Value of Authorization header, the token.
        """
        metadata_parse_req = {
            'orgUUID': acquisition_req.orgUUID,
            'publicRequest': acquisition_req.publicRequest,
            'source': acquisition_req.source,
            'category': acquisition_req.category,
            'title': acquisition_req.title,
            'id': acquisition_req.id,
            'callbackUrl': self._get_metadata_callback_url(acquisition_req.id)
        }
        if id_in_object_store:
            metadata_parse_req['idInObjectStore'] = id_in_object_store
        self._executor.submit(
            external_service_call,
            url=self._config.metadata_parser_url,
            data=metadata_parse_req,
            hidden_token=SecretString(req_auth))


class AcquisitionRequestsResource(DasResource):

    """
    Resource governing data acquisition (download) requests.
    """

    def __init__(self, req_store, executor, config):
        """
        :param `.acquisition_request.AcquisitionRequestStore` req_store:
        :param `rq.Queue` executor:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        super().__init__(req_store, executor, config)
        self._download_req_validator = Validator(schema={
            'category': {'type': 'string', 'required': True},
            'orgUUID': {'type': 'string', 'required': True},
            'publicRequest': {'type': 'boolean', 'required': True},
            'source': {'type': 'string', 'required': True},
            'title': {'type': 'string', 'required': True},
        })
        self._download_req_validator.allow_unknown = True
        self._org_checker = FalconUserOrgAccessChecker(config.user_management_url)

    def on_post(self, req, resp):
        """
        Requesting a new data set download.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        """
        acquisition_req = self._get_acquisition_req(req)
        self._org_checker.validate_access(req.auth, [acquisition_req.orgUUID])

        if acquisition_req.source.startswith('hdfs://'):
            acquisition_req.set_downloaded()
            self._req_store.put(acquisition_req)
            self._enqueue_metadata_request(acquisition_req, None, req.auth)
        else:
            self._req_store.put(acquisition_req)
            self._enqueue_downloader_request(acquisition_req, req.auth)

        resp.body = str(acquisition_req)
        resp.status = falcon.HTTP_ACCEPTED

    def on_get(self, req, resp):
        """
        Get acquisitions requests belonging to specific organizations,
        specified by a query parameter.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        """
        requested_orgs = req.params['orgs']
        if isinstance(requested_orgs, str): # only one org submitted
            requested_orgs = [requested_orgs]
        self._org_checker.validate_access(req.auth, requested_orgs)


        acquisition_request_lists = [self._req_store.get_for_org(org) for org in requested_orgs]
        acquisition_requests = itertools.chain(*acquisition_request_lists)
        resp.body = json.dumps([acq_req.__dict__ for acq_req in acquisition_requests])

    def _get_acquisition_req(self, req):
        """
        :param `falcon.Request` req:
        :returns: A parsed acquisition request sent to the service.
        :rtype: `.acquisition_request.AcquisitionRequestStore`
        :raises `falcon.HTTPBadRequest`: When the request is invalid.
        """
        req_json = self._parse_request(req, self._download_req_validator, 'download')
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
        self._executor.submit(
            external_service_call,
            url=self._config.downloader_url,
            data={
                'source': acquisition_req.source,
                'callback': self._get_download_callback_url(acquisition_req.id)
            },
            hidden_token=SecretString(req_auth))


class SingleAcquisitionRequestResource():

    """
    Resource for getting and deleting a single acquisition request.
    """

    def __init__(self, req_store, config):
        """
        :param `.acquisition_request.AcquisitionRequestStore` req_store:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        self._req_store = req_store
        self._org_checker = FalconUserOrgAccessChecker(config.user_management_url)

    def on_get(self, req, resp, req_id):
        """
        Getting a single acquisition request with its current status.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        :param str req_id: Request's ID.
        """
        try:
            acquisition_req = self._req_store.get(req_id)
            self._org_checker.validate_access(req.auth, [acquisition_req.orgUUID])
            resp.body = str(acquisition_req)
        except RequestNotFoundError:
            resp.status = falcon.HTTP_NOT_FOUND

    def on_delete(self, req, resp, req_id):
        """
        Getting a single acquisition request with its current status.
        :param `falcon.Request` req:
        :param `falcon.Response` resp:
        :param str req_id: Request's ID.
        """
        try:
            acquisition_req = self._req_store.get(req_id)
            self._org_checker.validate_access(req.auth, [acquisition_req.orgUUID])
            self._req_store.delete(acquisition_req)
        except RequestNotFoundError:
            resp.status = falcon.HTTP_NOT_FOUND


class DownloadCallbackResource(DasResource):

    """
    Resource accepting callbacks from the Downloader.
    """

    def __init__(self, req_store, executor, config):
        """
        :param `.acquisition_request.AcquisitionRequestStore` req_store:
        :param `rq.Queue` executor:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        super().__init__(req_store, executor, config)
        self._callback_validator = Validator(schema={
            'id': {'type': 'string', 'required': True},
            'state': {'type': 'string', 'required': True},
            'savedObjectId': {'type': 'string', 'required': True},
            'objectStoreId': {'type': 'string', 'required': True},
        })
        self._callback_validator.allow_unknown = True

    def on_post(self, req, _, req_id):
        """
        Callback after download of the data set.
        This will trigger a request to Metadata Parser.
        :param `falcon.Request` req:
        :param `falcon.Response` _:
        :param str req_id: ID given to the original acquisition request
        """
        req_json = self._parse_request(req, self._callback_validator, 'download callback')

        acquisition_req = self._req_store.get(req_id)
        if req_json['state'] == 'DONE':
            self._log.info('Acquisition request downloaded. Title: %s. ID: %s',
                           acquisition_req.title, acquisition_req.id)
            acquisition_req.set_downloaded()
            self._req_store.put(acquisition_req)
            self._enqueue_metadata_request(acquisition_req, req_json['savedObjectId'], req.auth)
        else:
            self._log.error('Acquisition request failed in Downloader. Title: %s. ID: %s',
                            acquisition_req.title, acquisition_req.id)
            acquisition_req.set_error()
            self._req_store.put(acquisition_req)


class UploaderResource(DasResource):

    """
    Resource accepting requests from Uploader.
    """

    def __init__(self, req_store, executor, config):
        """
        :param `.acquisition_request.AcquisitionRequestStore` req_store:
        :param `rq.Queue` executor:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        super().__init__(req_store, executor, config)
        self._uploader_req_validator = Validator(schema={
            'category': {'type': 'string', 'required': True},
            'orgUUID': {'type': 'string', 'required': True},
            'publicRequest': {'type': 'boolean', 'required': True},
            'source': {'type': 'string', 'required': True},
            'title': {'type': 'string', 'required': True},
            'idInObjectStore': {'type': 'string', 'required': True},
            'objectStoreId': {'type': 'string', 'required': False}
        })
        self._uploader_req_validator.allow_unknown = True

    def on_post(self, req, _):
        """
        Callback after download of the data set.
        This will trigger a request to Metadata Parser.
        :param `falcon.Request` req:
        :param `falcon.Response` _:
        """
        req_json = self._parse_request(req, self._uploader_req_validator, 'uploader request')

        acquisition_req = AcquisitionRequest(**req_json)
        acquisition_req.set_downloaded()

        self._req_store.put(acquisition_req)
        self._enqueue_metadata_request(acquisition_req, req_json['idInObjectStore'], req.auth)


class MetadataCallbackResource(DasResource):

    """
    Resource accepting callbacks from the Metadata Parser.
    """

    def __init__(self, req_store, config):
        """
        :param `.acquisition_request.AcquisitionRequestStore` req_store:
        :param `data_acquisition.DasConfig` config: Configuration object for the application.
        """
        # TODO this class should shouldn't inherit DasResource, maybe change it to composition
        super().__init__(req_store, None, config)
        self._callback_validator = Validator(schema={
            'state': {'type': 'string', 'required': True}
        })
        self._callback_validator.allow_unknown = True

    def on_post(self, req, _, req_id):
        """
        Callback after download of the data set.
        This will trigger a request to Metadata Parser.
        :param `falcon.Request` req:
        :param `falcon.Response` _:
        :param str req_id: ID given to the original acquisition request
        """
        req_json = self._parse_request(req, self._callback_validator, 'metadata callback')

        acquisition_req = self._req_store.get(req_id)
        if req_json['state'] == 'DONE':
            self._log.info('Acquisition request successful. Title: %s. ID: %s',
                           acquisition_req.title, acquisition_req.id)
            acquisition_req.set_finished()
            self._req_store.put(acquisition_req)
        else:
            self._log.error('Acquisition request failed in Metadata Parser. Title: %s. ID: %s',
                            acquisition_req.title, acquisition_req.id)
            acquisition_req.set_error()
            self._req_store.put(acquisition_req)

# TODO split this file into smaller ones
