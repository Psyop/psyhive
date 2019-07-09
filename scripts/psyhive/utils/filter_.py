"""Tools for applying text filters."""

import six

from psyhive.utils.misc import lprint


def apply_filter(list_, filter_, key=None, negate=False, case_sensitive=False):
    """Apply filter to a list.

    Args:
        list_ (list): list of items to filter
        filter_ (str): filter to apply
        key (fn): apply function to list items to get str to apply filter to
        negate (bool): invert the filter
        case_sensitive (bool): ignore case
    """
    _results = []
    for _item in list_:

        _passes_filter = passes_filter(
            _item, filter_, key=key, case_sensitive=case_sensitive)
        if not negate and _passes_filter:
            _results.append(_item)
        elif negate and not _passes_filter:
            _results.append(_item)

    return _results


def passes_filter(text, filter_, key=None, case_sensitive=False, verbose=0):
    """Check whether the given text passes the given filter.

    Args:
        text (str|any): text to check
        filter_ (str): filter to apply
        key (bool): function to apply to text to obtain text to apply filter to
        case_sensitive (bool): ignore case in text/filter
        verbose (int): print process data
    """
    if not filter_:
        return True

    _filter = filter_
    if not case_sensitive:
        _filter = _filter.lower()

    # Sort into filter tokens
    if '"' in _filter:
        _ftokens = []
        for _idx, _section in enumerate(_filter.split('"')):
            if not _section:
                continue
            if not _idx % 2:
                _ftokens += _section.split()
            else:
                _ftokens += [_section]
    else:
        _ftokens = _filter.split()

    # Parse filter str
    _matches = []
    _ignores = []
    _required = []
    for _ftoken in _ftokens:
        if _ftoken.startswith('+'):
            _required.append(_ftoken[1:])
        elif _ftoken.startswith('-'):
            _ignores.append(_ftoken[1:])
        else:
            _matches.append(_ftoken)

    # Get text to compare with
    if key:
        _text = key(text)
    else:
        if not isinstance(text, six.string_types):
            raise ValueError(text)
        _text = text
    if not case_sensitive:
        _text = _text.lower()
    lprint('TESTING', _text, verbose=verbose)

    # Check for required matches
    lprint(' - REQUIRED', _required, verbose=verbose)
    for _requirement in _required:
        if _requirement not in _text:
            return False

    # Check for matches
    lprint(' - MATCHES', _matches, verbose=verbose)
    if _matches and not [_match for _match in _matches if _match in _text]:
        lprint(' - NO MATCHES', verbose=verbose)
        return False

    # Check for ignores
    lprint(' - IGNORES', _ignores, verbose=verbose)
    for _ignore in _ignores:
        if _ignore in _text:
            return False

    return True
