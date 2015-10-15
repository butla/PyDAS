"""
Utility functions used by the tests.
"""
from falcon.testing import StartResponseMock, create_environ


def dict_is_part_of(dict_a, dict_b):
    """
    Checks whether dict_b is a part of dict_a.
    That is if dict_b is dict_a, just with some keys removed.
    :param dict dict_a:
    :param dict dict_b:
    :rtype: bool
    """
    for key, value in dict_b.items():
        if key not in dict_a or dict_a[key] != value:
            return False
    return True


def simulate_falcon_request(api, path='/', encoding=None, **kwargs):
    """Simulates a request to a `falcon.API`.

    Args:
        path (str): The path to request.
        decode (str, optional): If this is set to a character encoding,
            such as 'utf-8', `simulate_request` will assume the
            response is a single byte string, and will decode it as the
            result of the request, rather than simply returning the
            standard WSGI iterable.
        kwargs (optional): Same as those defined for
            `falcon.testing.create_environ`.

    """
    resp_headers = StartResponseMock()
    result = api(
        create_environ(path=path, **kwargs),
        resp_headers)

    final_result = result

    if encoding is not None:
        if result:
            final_result = result[0].decode(encoding)
        else:
            final_result = ''

    return final_result, resp_headers