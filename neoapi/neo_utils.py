__author__ = 'max'


def merge_dict(d1, d2):
    """ Merge two dictionaries, recursively. """

    result = d1

    # Overwrite with d2 items if necessary
    for k, v2 in d2.items():
        if k in d1:
            v1 = d1[k]

            if isinstance(v1, dict) and isinstance(v2, dict):
                result[k] = merge_dict(v1, v2)

        else:
            result[k] = v2

    return result