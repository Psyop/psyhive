"""Wrapper for maya.api.OpenMaya module."""

from maya_psyhive.open_maya.anim_curve import HFnAnimCurve
from maya_psyhive.open_maya.bounding_box import get_bbox
from maya_psyhive.open_maya.dependency_node import HFnDependencyNode
from maya_psyhive.open_maya.euler_rotation import HEulerRotation, get_r
from maya_psyhive.open_maya.matrix import HMatrix, get_m, axes_to_m
from maya_psyhive.open_maya.nurbs_curve import (
    HFnNurbsCurve, closed_curve, square)
from maya_psyhive.open_maya.nurbs_surface import HFnNurbsSurface
from maya_psyhive.open_maya.plug import HPlug
from maya_psyhive.open_maya.point import HPoint, get_p, ORIGIN
from maya_psyhive.open_maya.transform import HFnTransform
from maya_psyhive.open_maya.vector import HVector, X_AXIS, Y_AXIS, Z_AXIS
from maya_psyhive.open_maya.cmds import CMDS

LOC_SCALE = 1.0
LOC_COL = 'red'
