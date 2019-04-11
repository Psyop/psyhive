"""Tools for managing ranges of values."""

import sys


def ints_to_str(values, rng_sep="-", chunk_sep=","):
    """Convert a list on int values to a readable string.

    For example:

    [1, 2, 3] -> '1-3'
    [1, 2, 3, 5] -> '1-3,5'

    Args:
        values (int list): list of integers
        rng_sep (str): range separator (normally hyphen)
        chunk_sep (str): chunk separator (normally comma)
    """
    if not values:
        return ""

    if isinstance(values, (set, tuple)):
        values = list(values)

    values.sort()

    # Work out inc
    inc = None
    _min_inc = sys.maxsize
    seps = []
    for index, _this_val in enumerate(values[:-1]):

        _next_val = values[index+1]
        sep = _next_val-_this_val

        if sep == 0:
            raise RuntimeError("Found duplicate values in range "+str(values))
        elif sep == 1:
            inc = 1
            break
        elif sep < _min_inc:
            _min_inc = sep

        if sep not in seps:
            seps.append(sep)

    # Check all incs are divisible by inc
    if not seps:
        inc = 1
    elif not inc == 1:

        # Make sure all the seps are divisble by inc
        seps.sort()
        inc = seps[0]
        for sep in seps[1:]:
            if sep % inc:
                inc = 1
                break

    # Construct the string
    _val_str = str(values[0])
    if len(values) == 1:
        return _val_str
    elif values[0] == values[1]-inc:
        _val_str += rng_sep
    else:
        _val_str += chunk_sep

    for _prev_i, value in enumerate(values[1:-1]):

        _this_i = _prev_i+1
        _next_i = _this_i+1
        if value == values[_prev_i]+inc:  # A C

            if values[_next_i] == value+inc:  # A
                pass
            else:  # C
                _val_str += str(value)+chunk_sep

        else:  # B D

            if values[_next_i] == value+inc:  # B
                _val_str += str(value)+rng_sep
            else:  # D
                _val_str += str(value)+chunk_sep

    _val_str += str(values[-1])

    # Insert inc into string
    if not inc == 1:
        _new_str = ""
        for chunk in _val_str.split(chunk_sep):
            _new_str += chunk
            if rng_sep in chunk:
                _new_str += "x"+str(inc)
            _new_str += chunk_sep
        _val_str = _new_str.strip(chunk_sep)

    return _val_str


def str_to_ints(string, chunk_sep=",", rng_sep="-", end=None):
    """Convert a range string to a list of integers.

    For example:

    '1-5' -> [1, 2, 3, 4, 5]
    '1-2,4-5' -> [1, 2, 4, 5]

    Args:
        string (str): string to convert
        chunk_sep (str): chunk separator
        rng_sep (str): range separator
        end (int): force range end
    """
    if not string:
        return []

    _ints = []
    for _rng in string.split(chunk_sep):

        # Handle inc
        _inc = 1
        if "x" in _rng:
            assert _rng.count("x") == 1
            _rng, _inc = _rng.split("x")
            _inc = int(_inc)

        # Handle range
        _single_neg = (
            rng_sep == '-' and _rng.startswith('-') and _rng.count('-') == 1)
        if rng_sep in _rng and not _single_neg:

            # Read tokens
            _split = _rng.rfind(rng_sep)
            _tokens = [
                int(float(_val)) if _val else None
                for _val in (_rng[: _split], _rng[_split+1:])]

            # Convert to list of ints
            if _rng.endswith(rng_sep):
                assert end is not None
                _rng_start = _tokens[0]
                _rng_end = end
            else:
                _rng_start = _tokens[0]
                _rng_end = _tokens[-1]
            _ints += range(_rng_start, _rng_end+1, _inc)

        # Handle lone num
        else:
            _ints.append(int(_rng))

    return _ints
