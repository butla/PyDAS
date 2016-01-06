"""
Various functions used by the authorization/authentication layer.
"""

import logging
import requests

_log = logging.getLogger(__name__) #pylint: disable=invalid-name


def get_uaa_key(uaa_key_url):
    """
    Gets a key for verifying OAuth JWT tokens from CloudFoundry's UAA.
    :returns: UAA's public key.
    :raises `UaaError`: Getting the key from UAA failed.
    :rtype: str
    """
    try:
        response = requests.get(uaa_key_url)
    except requests.exceptions.ConnectionError as ex:
        msg = 'Failed to connect to UAA at {}'.format(uaa_key_url)
        _log.exception(msg)
        raise UaaError(msg) from ex

    if response.status_code != 200:
        msg = "Couldn't get UAA's public key.\nResponse code: {}\nMessage: {}".format(
            response.status_code,
            response.text
        )
        _log.error(msg)
        raise UaaError(msg)
    return response.json()['value']


class UaaError(Exception):
    """
    Happens when something goes wrong when contacting the UAA.
    """
    pass
