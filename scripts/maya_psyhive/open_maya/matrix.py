"""Matrix tools."""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique

from maya_psyhive.open_maya.vector import HVector
from maya_psyhive.open_maya.point import HPoint, ORIGIN


class HMatrix(om.MMatrix):
    """Represents a 4x4 heterozygous transformation matrix."""

    def apply_to(self, node):
        """Apply this matrix to the given node.

        Args:
            node (str): node to apply to
        """
        cmds.xform(node, matrix=self.to_tuple(), worldSpace=True)

    def build_geo(self, scale=1.0, name='HMatrix'):
        """Build geo to display this matrix.

        Args:
            scale (float): scale multiplier
            name (str): name for geo

        Returns:
            (str): group name
        """
        from maya_psyhive import open_maya as hom

        _grp = cmds.group(name=name, empty=True)
        for _col, _axis, _name in [
                ('red', hom.X_AXIS*scale, 'X'),
                ('green', hom.Y_AXIS*scale, 'Y'),
                ('blue', hom.Z_AXIS*scale, 'Z'),
        ]:
            _crv = _axis.build_crv(
                hom.ORIGIN, col=_col, name=get_unique(name+_name))
            cmds.parent(_crv, _grp)

        self.apply_to(_grp)

        return _grp

    def lx_(self):
        """Get local x-axis."""
        return HVector(self.to_tuple()[: 3])

    def ly_(self):
        """Get local y-axis."""
        return HVector(self.to_tuple()[4: 7])

    def lz_(self):
        """Get local z-axis."""
        return HVector(self.to_tuple()[8: 11])

    def pos(self):
        """Get translation."""
        _tm = om.MTransformationMatrix(self)
        return HPoint(_tm.translation(om.MSpace.kWorld))

    def to_tuple(self):
        """Convert to tuple.

        Returns:
            (float tuple): 16 floats
        """
        return tuple([self[_idx] for _idx in range(16)])

    def __str__(self):
        _vals = ''
        for _row in range(4):
            _vals += '[{}], '.format(
                ', '.join([
                    '{:.02f}'.format(self[_row*4+_idx])
                    for _idx in range(4)]))
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), _vals.strip(' ,'))


def axes_to_m(pos=None, lx_=None, ly_=None, lz_=None, verbose=0):
    """Convert axes and position to a matrix.

    Args:
        pos (HPoint): translation
        lx_ (HVector): local x axis
        ly_ (HVector): local y axis
        lz_ (HVector): local z axis
        verbose (int): print process data

    Returns:
        (HMatrix): tranformation matrix
    """
    _pos = pos or ORIGIN
    _lx = lx_
    _ly = ly_
    _lz = lz_
    del lx_, ly_, lz_, pos

    if _ly is None:
        lprint('CALCULATING LY', verbose=verbose)
        assert _lx
        assert _lz
        _ly = -(_lx ^ _lz).normalized()
    elif _lz is None:
        assert _lx
        assert _ly
        lprint('CALCULATING LZ', _lx.length(), _ly.length(), verbose=verbose)
        # print _lx, _ly, _lx^_ly
        _lz = (_lx ^ _ly).normalized()

    if verbose:
        print "LX", _lx, _lx.length()
        print "LY", _ly, _ly.length()
        print "LZ", _lz, _lz.length()

    return HMatrix([
        _lx[0], _lx[1], _lx[2], 0,
        _ly[0], _ly[1], _ly[2], 0,
        _lz[0], _lz[1], _lz[2], 0,
        _pos[0], _pos[1], _pos[2], 1])


def get_m(node):
    """Get matrix of the given node.

    Args:
        node (str): node to read matrix of
    """
    return HMatrix(
        cmds.xform(node, query=True, matrix=True, worldSpace=True))