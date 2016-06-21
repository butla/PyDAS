"""
Things related to types of requests that come in and out of the app.
"""

import json
import time
import uuid


class RequestNotFoundError(Exception):
    """Signals that a request wasn't found in a `AcquisitionRequestStore`."""
    pass


class AcquisitionRequestStore:
    """Abstraction over Redis for storage and retrieval of `AcquisitionRequest` objects.

    Args:
        redis_client (`redis.Redis`): Redis client.
    """

    REDIS_HASH_NAME = 'requests'

    def __init__(self, redis_client):
        self._redis = redis_client

    @staticmethod
    def get_request_redis_id(acquisition_req):
        """
        Args:
            acquisition_req (`AcquisitionRequest`): An acquisition request.

        Returns:
            str: Key under which the request can be stored in Redis.
        """
        return '{}:{}'.format(acquisition_req.orgUUID, acquisition_req.id)

    def put(self, acquisition_req):
        """Put an acquisition request in the store (Redis).

        Args:
            acquisition_req (`AcquisitionRequest`): A request that will be put in store.
        """
        self._redis.hset(
            self.REDIS_HASH_NAME,
            self.get_request_redis_id(acquisition_req),
            str(acquisition_req)
        )

    def get(self, req_id):
        """Get an acquisition request in the store (Redis).

        Args:
            req_id (str): Identifier of the individual request.

        Returns:
            `AcquisitionRequest`: The request with the given ID.

        Raises:
            `RequestNotFoundError`: Request with the given ID doesn't exist.
        """
        entries = self._redis.hgetall(self.REDIS_HASH_NAME)
        try:
            entry = next(value for key, value in entries.items() if key.endswith(req_id.encode()))
        except StopIteration:
            raise RequestNotFoundError('No request for ID {}'.format(req_id))
        req_json = json.loads(entry.decode())
        return AcquisitionRequest(**req_json)

    def delete(self, acquisition_req):
        """Delete an acquisition request from the store (Redis).

        Args:
            acquisition_req (`AcquisitionRequest`): Request with the same ID will be deleted
                from the store.
        """
        self._redis.hdel(
            self.REDIS_HASH_NAME,
            self.get_request_redis_id(acquisition_req))

    def get_for_org(self, org_id):
        """
        Args:
            org_id (str): Organization's UUID.

        Returns:
            list[`AcquisitionRequest`]: All requests for the given organization.
        """
        entries = self._redis.hgetall(self.REDIS_HASH_NAME)
        filtered = (value.decode() for key, value in entries.items()
                    if key.startswith(org_id.encode()))
        return [AcquisitionRequest(**json.loads(req_str)) for req_str in filtered]

    # TODO get all (for admin only)


class AcquisitionRequest: #pylint: disable=too-many-instance-attributes

    """
    Data set download request.
    """

    def __init__(self, title, orgUUID, publicRequest, source, category, #pylint: disable=too-many-arguments
                 state='NEW', id=None, timestamps=None, **_): #pylint: disable=redefined-builtin
        """
        :param str title:
        :param str orgUUID:
        :param bool publicRequest:
        :param str source:
        :param str category:
        :param str state:
        :param str id:
        :param dict timestamps:
        :param __: Ignored keyword arguments. Eases deserialization with unknown fields.
        """
        self.orgUUID = orgUUID #pylint: disable=invalid-name
        self.publicRequest = publicRequest #pylint: disable=invalid-name
        self.source = source
        self.category = category
        self.title = title
        self.state = state
        if id:
            self.id = id #pylint: disable=invalid-name,redefined-builtin
        else:
            self.id = str(uuid.uuid4())
        if not timestamps:
            self.timestamps = {}
        else:
            self.timestamps = dict(timestamps)

    def __str__(self):
        return json.dumps(self.__dict__)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return '{}({})'.format(type(self), repr(self.__dict__))

    def __hash__(self):
        return hash(self.id)

    def set_validated(self):
        """
        Sets the state of the object to validated.
        """
        self._set_state('VALIDATED')

    def set_downloaded(self):
        """
        Sets the state of the object to downloaded.
        """
        self._set_state('DOWNLOADED')

    def set_finished(self):
        """
        Sets the state of the object to finished.
        """
        self._set_state('FINISHED')

    def set_error(self):
        """
        Sets the state of the object to "error" after a failure.
        """
        self._set_state('ERROR')

    def _set_state(self, state):
        """
        Sets the state of the object and adds the timestamp of state transition.
        :param str state: Name of the new state.
        :rtype: None
        """
        self.state = state
        self.timestamps[state] = int(time.time())
