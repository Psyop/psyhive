"""General utilites for qt wrapper."""

from .qtw_mgr import QtCore


def get_rect(anchor, pos, size):
    """Get rect for the given pos/size and anchor position.

    Args:
        anchor (str): anchor point
        pos (QPoint): anchor position
        size (QSize): rect size

    Returns:
        (QRect): rectangle
    """
    from psyhive import qt

    _size = qt.get_size(size)
    _pos = qt.get_p(pos)
    if anchor == 'C':
        _root = _pos - qt.get_p(_size)/2
    elif anchor == 'L':
        _root = _pos - qt.get_p(0, _size.height()/2)
    elif anchor == 'R':
        _root = _pos - qt.get_p(_size.width(), _size.height()/2)
    elif anchor == 'T':
        _root = _pos - qt.get_p(_size.width()/2, 0)
    elif anchor == 'TL':
        _root = _pos
    elif anchor == 'TR':
        _root = _pos - qt.get_p(_size.width(), 0)
    elif anchor == 'BL':
        _root = _pos - qt.get_p(0, _size.height())
    elif anchor == 'BR':
        _root = _pos - qt.get_p(_size.width(), _size.height())
    else:
        raise ValueError(anchor)

    return QtCore.QRect(_root, _size)
