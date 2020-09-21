"""General utilities for ingestion.

NOTE: these need to work outside psyop so should not include any
psyop pipeline modules, eg. tank.
"""

from psyhive.utils import get_single, abs_path

INGESTED_TOKEN = 'ingested 11/09/20'


def _is_ver(token):
    """Test if the given token is a valid verison (eg. v001).

    Args:
        token (str): token to test

    Returns:
        (bool): whether token is version
    """
    return len(token) == 4 and token[0] == 'v' and token[1:].isdigit()


def parse_basename(basename):
    """Parse basename of the given vendor file.

    File basenames must follow this convention:

        - <tag>_<step>_<version>

    Args:
        basename (str): basename to parse

    Returns:
        (str tuple): tag/step/version data
    """
    _tag, _step, _layer, _ver, _aov = parse_seq_basename(basename)
    if _aov:
        raise ValueError("Aov in basename: {}".format(_aov))
    if _layer:
        raise ValueError("Layer in basename: {}".format(_layer))
    return _tag, _step, _ver


def parse_seq_basename(basename):
    """Parse basename of the given image sequence.

    Sequence basenames must follow one of these 3 conventions:

        - <tag>_<step>_<version>
        - <tag>_<step>_<layer>_<version>
        - <tag>_<step>_<layer>_<version>_<aov>

    Args:
        basename (str): basename to parse

    Returns:
        (str tuple): tag/step/layer/version/aov data
    """
    _tokens = basename.split('_')
    _tag, _step = _tokens[:2]
    _ver = get_single([_token for _token in _tokens if _is_ver(_token)])
    _layer = '_'.join(_tokens[2: _tokens.index(_ver)]) or None
    _aov = '_'.join(_tokens[_tokens.index(_ver)+1:]) or None
    return _tag, _step, _layer, _ver, _aov


def vendor_from_path(path):
    """Try to get vendor from the given delivery path.

    Args:
        path (str): path to read

    Returns:
        (str|None): vendor name (if any)
    """
    _tokens = abs_path(path).split('/')
    for _parent in ['vendor_in']:
        if _parent in _tokens and not _parent == _tokens[-1]:
            return _tokens[_tokens.index(_parent)+1]

    return None
