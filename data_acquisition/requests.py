"""
Things related to types of requests that come in and out of the app.
"""

import json
import uuid


# TODO maybe there can be a request base with the five attributes and then inheriting ones
class AcquisitionRequestStore:

    """
    Abstraction over Redis for storage and retrieval of `AcquisitionRequest` objects.
    """

    def __init__(self, redis_client):
        """
        :param `redis.Redis` redis_client: Redis client.
        """
        self._redis = redis_client

    def put(self, acquisition_req):
        """
        :param `AcquisitionRequest` acquisition_req:
        :return:
        """
        self._redis.set(
            '{}:{}'.format(acquisition_req.orgUUID, acquisition_req.id),
            str(acquisition_req)
        )

    def get(self, req_id):
        """
        :param str req_id: Identifier of the individual request.
        :return: The request with the give ID.
        :rtype: AcquisitionRequest
        """
        keys = self._redis.keys('*:{}'.format(req_id))
        req_json = json.loads(self._redis.get(keys[0]).decode())
        return AcquisitionRequest(**req_json)


class AcquisitionRequest:

    """
    Data set download request.
    """

    def __init__(self, title, orgUUID, publicRequest, source, category,
                 status='VALIDATED', id=None):
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

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __repr__(self):
        return '{}({})'.format(type(self), repr(self.__dict__))
