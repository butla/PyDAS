"""
Utility functions used by tests.
"""

from requests.structures import CaseInsensitiveDict


def dict_is_part_of(dict_a, dict_b):
    """
    Checks whether dict_b is a part of dict_a.
    That is if dict_b is dict_a, just with some keys removed.
    :param dict dict_a:
    :param dict dict_b:
    :rtype: bool
    """
    dict_a, dict_b = CaseInsensitiveDict(dict_a), CaseInsensitiveDict(dict_b)
    for key, value in dict_b.items():
        if key not in dict_a or dict_a[key] != value:
            return False
    return True
