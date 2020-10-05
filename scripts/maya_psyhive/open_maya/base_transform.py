"""Tools for managing the base transform node class."""

from maya import cmds

from psyhive.utils import get_single, lprint
from maya_psyhive.utils import add_to_grp, set_col, get_shp

from .base_node import BaseNode
from .plug import HPlug
from .point import ORIGIN


class BaseTransform(BaseNode):
    """Base class for any transform object."""

    def __init__(self, node, verbose=0):
        """Constructor.

        Args:
            node (str): tranform node name
            verbose (int): print process data
        """
        from maya_psyhive import open_maya as hom
        super(BaseTransform, self).__init__(node)

        # Get shape (if any)
        _shps = cmds.listRelatives(
            self.node, shapes=True, path=True, noIntermediate=True) or []
        _shp = get_single([str(_shp) for _shp in _shps], catch=True)
        self.shp = hom.HFnDependencyNode(_shp) if _shp else None
        lprint('SHAPE', self.shp, _shps, verbose=verbose)

        # Create plugs
        for _param in 'trs':
            for _axis in 'xyz':
                _attr = _param+_axis
                _plug = HPlug(self.node+'.'+_attr)
                setattr(self, _attr, _plug)
        self.translate = HPlug(self.node+'.translate')
        self.rotate = HPlug(self.node+'.rotate')
        self.scale = HPlug(self.node+'.scale')
        self.visibility = HPlug(self.node+'.visibility')

    def add_u_scale(self):
        """Add uniform scale attribute to control scale xyz atts.

        Returns:
            (HPlug): uniform scale
        """
        _u_scale = self.create_attr('uScale', 1.0)
        _u_scale.connect(self.scale, axes='XYZ')
        return _u_scale

    def add_to_grp(self, grp):
        """Add this node to a group, creating it if required.

        Args:
            grp (str): group to add to
        """
        from maya_psyhive import open_maya as hom
        return hom.HFnTransform(add_to_grp(self, grp))

    def aim_constraint(self, *args, **kwargs):
        """Aim constrain a node to this node.

        Returns:
            (HFnTransform): aim constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.aimConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def bbox(self):
        """Get this node's bounding box.

        Returns:
            (HBoundingBox): bounding box
        """
        from maya_psyhive import open_maya as hom
        return hom.get_bbox(str(self))

    def delete_history(self):
        """Delete this node's history."""
        cmds.delete(self, constructionHistory=1)

    def flush(self):
        """Flush this object's transformations.

        This means resetting the pivot, freezing transform and
        deleting history.
        """
        self.set_pivot()
        self.freeze_transforms()
        self.delete_history()

    def freeze_transforms(self, translate=True, rotate=True, scale=True):
        """Freeze transforms on this node.

        Args:
            translate (bool): freeze translation
            rotate (bool): freeze rotation
            scale (bool): freeze scale
        """
        _kwargs = dict(
            apply=True, translate=translate, rotate=rotate, scale=scale,
            normal=False, preserveNormals=True)
        cmds.makeIdentity(self, **_kwargs)

    def hide(self):
        """Hide this node."""
        self.visibility.set_val(False)

    def get_m(self):
        """Get matrix of this object's transform.

        Returns:
            (HMatrix): matrix
        """
        from maya_psyhive import open_maya as hom
        return hom.get_m(self)

    def get_p(self):
        """Get position of this transform.

        Returns:
            (HPoint): position
        """
        from maya_psyhive import open_maya as hom
        return hom.get_p(self)

    def get_shp(self):
        """Find this node's shape.

        Returns:
            (HFnDependencyNode): shape
        """
        from maya_psyhive import open_maya as hom
        _shp = get_shp(self)
        return hom.HFnDependencyNode(_shp) if _shp else None

    def orient_constraint(self, *args, **kwargs):
        """Orient constrain a node to this node.

        Returns:
            (HFnTransform): orient constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.orientConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def parent(self, *args, **kwargs):
        """Wrapper for cmds.parent command."""
        cmds.parent(self, *args, **kwargs)

    def parent_constraint(self, *args, **kwargs):
        """Parent constrain a node to this node.

        Returns:
            (HFnTransform): parent constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.parentConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def point_constraint(self, *args, **kwargs):
        """Point constrain a node to this node.

        Returns:
            (HFnTransform): point constraint
        """
        from maya_psyhive import open_maya as hom
        _constr = cmds.pointConstraint(self, *args, **kwargs)[0]
        return hom.HFnTransform(_constr)

    def reset_transforms(self):
        """Reset transforms on this node."""
        self.translate.set_val((0, 0, 0))
        self.rotate.set_val((0, 0, 0))
        self.scale.set_val((1, 1, 1))

    def set_col(self, col):
        """Set colour of this node in maya viewport.

        Args:
            col (str): colour to apply
        """
        set_col(str(self), col)

    def set_p(self, pos):
        """Set position of this node.

        Args:
            pos (HPoint): position to apply
        """
        cmds.xform(self, translation=(pos[0], pos[1], pos[2]), worldSpace=True)

    def set_pivot(self, pos=None, scale=True, rotate=True):
        """Set this node's scale/rotate pivot.

        Args:
            pos (HPoint): position (if not origin)
            scale (bool): apply to scale pivot
            rotate (bool): apply to rotate pivot
        """
        _pos = pos or ORIGIN
        for _tgl, _plug in [
                (scale, self.plug('scalePivot')),
                (rotate, self.plug('rotatePivot'))]:
            if _tgl:
                cmds.move(_pos[0], _pos[1], _pos[2], _plug)

    def set_key(self):
        """Set keyframe on this node."""
        cmds.setKeyframe(self)

    def show(self):
        """Hide this node."""
        self.visibility.set_val(True)

    def u_scale(self, scale):
        """Apply a uniform scale to this node.

        Args:
            scale (float): scale value
        """
        assert isinstance(scale, (int, float))
        self.scale.set_val([scale, scale, scale])
