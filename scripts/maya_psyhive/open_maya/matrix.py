"""Matrix tools."""

import math

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint
from maya_psyhive.utils import get_unique

from maya_psyhive.open_maya.utils import cast_result
from maya_psyhive.open_maya.vector import HVector
from maya_psyhive.open_maya.point import ORIGIN


class HMatrix(om.MMatrix):
    """Represents a 4x4 heterozygous transformation matrix."""

    inverse = cast_result(om.MMatrix.inverse)
    __mul__ = cast_result(om.MMatrix.__mul__)
    __sub__ = cast_result(om.MMatrix.__sub__)

    def apply_to(self, node, use_constraint=False):
        """Apply this matrix to the given node.

        Args:
            node (str): node to apply to
            use_constraint (bool): use constraints to apply move
        """
        if use_constraint:
            _loc = self.build_loc()
            _parent_cons = cmds.parentConstraint(
                _loc, node, maintainOffset=False)[0]
            _scale_cons = cmds.scaleConstraint(
                _loc, node, maintainOffset=False)[0]
            cmds.delete(_loc, _parent_cons, _scale_cons)
            return

        cmds.xform(node, matrix=self, worldSpace=True)

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

    def build_loc(self, name=None, **kwargs):
        """Build locator using this matrix.

        Args:
            name (str): override name
        """
        from maya_psyhive import open_maya as hom
        _name = name or type(self).__name__.strip('_')
        _loc = hom.build_loc(name=get_unique(_name), **kwargs)
        self.apply_to(_loc)
        return _loc

    def get_bearing(self):
        """Get bearing of this matrix's rotation.

        This is the angle in the XZ plane facing down (-Y). The
        result is clamped in the range 0-360.

        Returns:
            (float): bearing
        """
        return math.degrees(-self.rot().y) % 360

    def get_pitch(self, build_geo=False):
        """Get pitch of this matrix's rotation.

        The is the angle which the local z (forward) axis makes
        with the horizontal and is clamped in the range 0-360.

        Args:
            build_geo (bool): build test geo

        Returns:
            (float): pitch
        """
        _lz = self.lz_()
        return _lz.get_pitch(build_geo=build_geo)

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
        from maya_psyhive import open_maya as hom
        _tm = om.MTransformationMatrix(self)
        return hom.HPoint(_tm.translation(om.MSpace.kWorld))

    def pprint(self, dp_=3):
        """Print this matrix in a readable form.

        Args:
            dp_ (int): accuracy in decimal points
        """
        _fmt = '{{:8.0{:d}f}}'.format(dp_)
        _str = ''
        for _idx, _val in enumerate(self.to_tuple()):
            _str += (_fmt+', ').format(_val)
            if not (_idx + 1) % 4:
                _str += '\n'

        print _str

    def rot(self):
        """Get rotation.

        Returns:
            (HEulerRotation): rotation component
        """
        from maya_psyhive import open_maya as hom
        _tm = om.MTransformationMatrix(self)
        return hom.HEulerRotation(_tm.rotation())

    def scale(self):
        """Get translation."""
        from maya_psyhive import open_maya as hom
        _tm = om.MTransformationMatrix(self)
        return hom.HPoint(_tm.scale(om.MSpace.kWorld))

    def to_tuple(self):
        """Convert to tuple.

        Returns:
            (float tuple): 16 floats
        """
        return tuple([self[_idx] for _idx in range(16)])

    def __eq__(self, other):
        for _this_v, _other_v in zip(self, other):
            if round(_this_v - _other_v, 12):
                return False
        return True

    def __str__(self):
        _vals = ''
        for _row in range(4):
            _vals += '[{}], '.format(
                ', '.join([
                    '{:.02f}'.format(self[_row*4+_idx])
                    for _idx in range(4)]))
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), _vals.strip(' ,'))

    __repr__ = __str__


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
        _lz = (_lx ^ _ly).normalized()
    elif _lx is None:
        assert _lz
        assert _ly
        lprint('CALCULATING LY', _ly.length(), _lz.length(), verbose=verbose)
        _lx = (_lz ^ _ly).normalized()

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
