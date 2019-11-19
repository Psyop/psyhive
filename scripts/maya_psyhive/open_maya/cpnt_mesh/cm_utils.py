"""Utilties for managing mesh components."""

import pprint

from maya import cmds

from psyhive.utils import str_to_ints, lprint


def _flatten(cpnts, verbose=0):
    """Separate a lists of compounded components.

    eg. ['geo.map[0:1]', 'geo.map[3]']
    ->  ['geo.map[0]', 'geo.map[1]', 'geo.map[3]']

    Args:
        cpnts (str list): component list
        verbose (int): print process data

    Returns:
        (str list): flattened list
    """
    _flat = []
    for _cpnt in cpnts:
        _rng = _cpnt.split('[')[-1].strip(']')
        if _rng.isdigit():
            _flat.append(str(_cpnt))
        elif _rng == '*':

            _root = _cpnt.split('[')[0]
            _mesh, _attr = _root.split('.')
            _eval = cmds.polyEvaluate(_mesh)

            if verbose:  # For speed
                lprint('EVAL', pprint.pformat(_eval))

            _count = _eval[{
                'e': 'edge',
                'f': 'face',
                'vtx': 'vertex',
                'map': 'uvcoord',
            }[_attr]]
            _flat += ['{}[{:d}]'.format(_root, _idx)
                      for _idx in range(_count)]

        else:
            _idxs = str_to_ints(_rng, rng_sep=':')
            _root = _cpnt.split('[')[0]
            _flat += ['{}[{:d}]'.format(_root, _idx) for _idx in _idxs]

    return _flat


def to_edges(cpnt):
    """Convert a component to edges.

    Args:
        cpnt (str|str list): component(s) to convert

    Returns:
        (str list): edges
    """
    return _flatten(cmds.polyListComponentConversion(cpnt, toEdge=True))


def to_faces(cpnt):
    """Convert a component to faces.

    Args:
        cpnt (str|str list): component(s) to convert

    Returns:
        (str list): faces
    """
    return _flatten(cmds.polyListComponentConversion(cpnt, toFace=True))


def to_uvs(cpnt):
    """Convert a component to uvs.

    Args:
        cpnt (str|str list): component(s) to convert

    Returns:
        (UV list): uvs
    """
    return _flatten(cmds.polyListComponentConversion(cpnt, toUV=True))


def to_vtxs(cpnt):
    """Convert a component to vertices.

    Args:
        cpnt (str|str list): component(s) to convert

    Returns:
        (str list): vertices
    """
    return _flatten(cmds.polyListComponentConversion(cpnt, toVertex=True))
