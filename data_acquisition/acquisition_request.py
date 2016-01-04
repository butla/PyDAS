"""
Things related to types of requests that come in and out of the app.
"""

import json
import time
import uuid


class RequestNotFoundError(Exception):
    """
    Signals that a request wasn't found in a `AcquisitionRequestStore`.
    """
    pass


class AcquisitionRequestStore:

    """
    Abstraction over Redis for storage and retrieval of `AcquisitionRequest` objects.
    """

    REDIS_HASH_NAME = 'requests'

    def __init__(self, redis_client):
        """
        :param `redis.Redis` redis_client: Redis client.
        """
        self._redis = redis_client

    def put(self, acquisition_req):
        """
        :param `AcquisitionRequest` acquisition_req: A request that will be put in store.
        """
        self._redis.hset(
            self.REDIS_HASH_NAME,
            '{}:{}'.format(acquisition_req.orgUUID, acquisition_req.id),
            str(acquisition_req)
        )

    def get(self, req_id):
        """
        :param str req_id: Identifier of the individual request.
        :return: The request with the given ID.
        :rtype: AcquisitionRequest
        :raises RequestNotFoundError: Request with the given ID doesn't exist.
        """
        entries = self._redis.hgetall(self.REDIS_HASH_NAME)
        try:
            entry = next(value for key, value in entries.items() if key.endswith(req_id.encode()))
        except StopIteration:
            raise RequestNotFoundError('No request for ID {}'.format(req_id))
        req_json = json.loads(entry.decode())
        return AcquisitionRequest(**req_json)

    def delete(self, acquisition_req):
        """
        :param `AcquisitionRequest` acquisition_req: A request that will be put in store.
        """
        self._redis.hdel(
            self.REDIS_HASH_NAME,
            '{}:{}'.format(acquisition_req.orgUUID, acquisition_req.id))

    def get_for_org(self, org_id):
        """
        :param str org_id: Organization's UUID.
        :return: All requests for the given organization.
        :rtype: list[AcquisitionRequest]
        """
        entries = self._redis.hgetall(self.REDIS_HASH_NAME)
        filtered = (value.decode() for key, value in entries.items()
                    if key.startswith(org_id.encode()))
        return [AcquisitionRequest(**json.loads(req_str)) for req_str in filtered]

    # TODO get all (for admin only)


class AcquisitionRequest:

    """
    Data set download request.
    """

    def __init__(self, title, orgUUID, publicRequest, source, category,
                 state='NEW', id=None, timestamps=None, **__):
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
        self.orgUUID = orgUUID
        self.publicRequest = publicRequest
        self.source = source
        self.category = category
        self.title = title
        self.state = state
        if id:
            self.id = id
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
