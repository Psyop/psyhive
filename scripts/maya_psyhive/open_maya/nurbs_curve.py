"""Tools for managing nurbs curves."""

from maya import cmds
from maya.api import OpenMaya as om

from psyhive.utils import lprint, store_result
from maya_psyhive.utils import get_unique, set_col, multiply_node

from maya_psyhive.open_maya.base_transform import BaseTransform
from maya_psyhive.open_maya.dag_path import HDagPath
from maya_psyhive.open_maya.matrix import axes_to_m
from maya_psyhive.open_maya.point import HPoint
from maya_psyhive.open_maya.vector import HVector, Y_AXIS, Z_AXIS


class HFnNurbsCurve(BaseTransform, om.MFnNurbsCurve):
    """Represent a nurbs curve."""

    def __init__(self, tfm):
        """Constructor.

        Args:
            tfm (str): curve transform
        """
        self.tfm = tfm
        super(HFnNurbsCurve, self).__init__(self.tfm)
        _dag_path = HDagPath(self.shp.node)
        om.MFnNurbsCurve.__init__(self, _dag_path)
        self.world_space = self.shp.plug('worldSpace')
        self.create = self.shp.plug('create')

    def close(self):
        """Close this curve (slow)."""
        cmds.closeCurve(self, replaceOriginal=True)

    def cv_p(self, idx):
        """Get the position of the given cv.

        Args:
            idx (int): cv index

        Returns:
            (HPoint): cv position
        """
        return HPoint(self.cvPosition(idx))

    def cv_ps(self):
        """Get a list of this curve's cv positions.

        Returns:
            (HPoint list): cv positions
        """
        return [self.cv_p(_cv) for _cv in range(self.numCVs)]

    def len_(self, safe=True):
        """Get the length of this curve.

        The OpenMaya method returns the unscaled lenght, which can be
        unsafe. Using cmds.arclen is slower but more reliable.

        Args:
            safe (bool): use cmds.arclen (slow)

        Returns:
            (float): curve length
        """
        if safe:
            return cmds.arclen(self.shp)

        # Check for scale issues
        _scale = self.get_m().scale()
        if round(_scale.x-_scale.y, 4) or round(_scale.x-_scale.z, 4):
            raise RuntimeError(
                "The curve %s has non-uniform scale %s - the length cannot "
                "be calculated accurately using the length function. You "
                "can freeze transforms, or use the slower safe mode." % (
                    (self.T, _scale)))

        return self.length()*_scale.x

    def motion_path(self, trg, add_u_length=False):
        """Attach the target mode this curve using a motion path.

        This uses the pathAnimation command, and deletes the default
        animation and placeholder applied to the u value.

        Args:
            trg (str|HFnTransform): transform to attach

        Returns:
            (MFnDependencyNode): motion path node
        """
        from maya_psyhive import open_maya as hom
        _mpath = hom.CMDS.pathAnimation(
            trg, self, follow=True, fractionMode=True)
        _u_val = _mpath.plug('uValue')
        _u_val.break_connections()
        if add_u_length:
            _ci = self.obtain_curve_info()
            _length = _ci.plug('arcLength')
            print 'CURVE INFO', _ci
            print _length.get_attr()
            _u_len = _mpath.add_attr('uLength', 0.0)
            multiply_node(_length, _u_val, _u_len)
        return _mpath

    def mtx_at_fr(
            self, fr_, project=False, safe=True, world_space=True,
            up_=None):
        """Get the matrix at the given position fraction on this curve.

        Args:
            fr_ (float): position fraction
            project (bool): project past start/end for values outside 0-1
            safe (bool): use slow length function
            world_space (bool): use world space
            up_ (HVector): override up vector

        Returns:
            (HMatrix): matrix
        """
        _l = self.len_(safe=safe)*fr_
        return self.mtx_at_len(
            _l, project=project, world_space=world_space, up_=up_)

    def mtx_at_len(
            self, length, project=False, world_space=False, up_=None):
        """Get matrix at given curve position.

        Args:
            length (float): position on curve
            project (bool): project past start/end for values outside 0-1
            world_space (bool): use world space
            up_ (HVector): override up vector

        Returns:
            (HMatrix): matrix
        """
        _param = self.findParamFromLength(length)
        _mtx = self.mtx_at_param(
            _param, world_space=world_space, up_=up_)

        if project:

            # Find curve offset
            if length < 0:
                _dl = length
            elif length > self.length():
                _dl = length-self.length()
            else:
                _dl = 0

            # Project offset
            if _dl:
                _mtx = (Z_AXIS*_dl).toM() * _mtx

        return _mtx

    def mtx_at_param(
            self, param, turn_on_percentage=None, world_space=None, up_=None):
        """Get matrix at given parametric length on curve.

        Args:
            param (float): parametric position
            turn_on_percentage (bool): use fractional parameter
            world_space (bool): use world space
            up_ (HVector): override up vector

        Returns:
            (HMatrix): matrix
        """
        _pos = self.p_at_param(
            param, turn_on_percentage=turn_on_percentage, world_space=world_space)
        _lz = self.t_at_param(
            param, turn_on_percentage=turn_on_percentage)
        if up_:
            _ly = up_.normalized()
            _lx = (-_lz ^ _ly).normalized()
        else:
            _lx = (-_lz ^ Y_AXIS).normalized()
            _ly = (-_lx ^ _lz).normalized()
        _mtx = axes_to_m(pos=_pos, lx_=_lx, ly_=_ly, lz_=_lz)
        return _mtx

    @store_result
    def obtain_curve_info(self):
        from maya_psyhive import open_maya as hom

        _cis = self.world_space.list_connections(type='curveInfo')
        if _cis:
            return asdasdas

        _ci = hom.CMDS.createNode('curveInfo')
        self.world_space.connect(_ci.plug('inputCurve'))
        return _ci

    def p_at_fr(self, fr_, safe=True, world_space=True):
        """Get point on curve at the given fractional position.

        Args:
            fr_ (float): curve fraction
            safe (bool): use slow length function
            world_space (bool): use world space

        Returns:
            (HPoint): curve position
        """
        if not isinstance(fr_, (float, int)):
            raise TypeError(fr_)
        return self.mtx_at_fr(
            fr_, safe=safe, world_space=world_space).pos()

    def p_at_param(self, param, world_space=True, turn_on_percentage=False):
        """Get curve position at given parametric length on curve.

        Args:
            param (float): parametric position
            world_space (bool): use world space
            turn_on_percentage (bool): use fractional parameter

        Returns:
            (HPoint): curve position
        """
        _param = param
        if turn_on_percentage:
            _param = self._fractionToParam(_param)
        _pt = self.getPointAtParam(
            _param, om.MSpace.kWorld if world_space else om.MSpace.kObject)
        return HPoint(_pt)

    def t_at_param(self, param, turn_on_percentage=False):
        """Get curve tangent at given parametric length on curve.

        Args:
            param (float): parametric position
            turn_on_percentage (bool): use fractional parameter

        Returns:
            (HVector): curve tangent
        """
        _param = param
        if turn_on_percentage:
            _param = self._fractionToParam(_param)
        _tan = HVector(self.tangent(_param))
        return _tan.normalized()


def closed_curve(point, name='curve', degree=3, col=None, verbose=0):
    """Build a closed curve from a list of point.

    Args:
        point (HPoint list): list of points
        name (str): curve name
        degree (int): curve degree
        col (str): viewport colour
        verbose (int): print process data

    Returns:
        (HFnNurbCurve): closed curve
    """
    from maya_psyhive import open_maya as hom

    if degree == 1:
        _pts = list(point) + [point[0]]
        _knot = range(len(_pts))
    elif degree == 3:
        _pts = list(point) + point[:3]
        _knot = [float(_idx) for _idx in range(-2, len(_pts))]
    else:
        raise NotImplementedError
    lprint("POINT", len(_pts), _pts, verbose=verbose)
    lprint("KNOT", len(_knot), _knot, verbose=verbose)

    _name = get_unique(name)
    _crv = hom.CMDS.curve(
        point=_pts, periodic=True, knot=_knot, degree=degree, name=_name)
    if col:
        set_col(_crv.tfm, col)
    return _crv


def square(name='square', width=1.0):
    """Build a square.

    Args:
        name (str): name for square
        width (float): square widget

    Returns:
        (HFnNurbCurve): square
    """
    from maya_psyhive import open_maya as hom

    _pts = [(1, 1, 0), (-1, 1, 0), (-1, -1, 0), (1, -1, 0), (1, 1, 0)]
    _square = hom.CMDS.curve(
        point=_pts, periodic=True, knot=range(5),
        degree=1, name=get_unique(name))
    cmds.rotate(90, 0, 0)
    _scale = width/2
    cmds.scale(_scale, _scale, _scale)
    _square.flush()

    return _square
