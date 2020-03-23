"""Wrapper for maya.api.OpenMaya module."""

from .anim_curve import HFnAnimCurve
from .base_array3 import BaseArray3
from .bounding_box import get_bbox, HBoundingBox
from .camera import HFnCamera, get_active_cam
from .dag_path import HDagPath
from .dependency_node import HFnDependencyNode
from .euler_rotation import HEulerRotation, get_r
from .matrix import HMatrix, get_m, axes_to_m
from .mesh import HFnMesh
from .nurbs_curve import (
    HFnNurbsCurve, closed_curve, square)
from .nurbs_surface import HFnNurbsSurface
from .plane import HPlane
from .plug import HPlug
from .point import HPoint, get_p, ORIGIN
from .transform import HFnTransform
from .ray import HVRay
from .utils import (
    build_loc, build_arrow, get_selected, lerp, sph_rand, get_col)
from .vector import HVector, X_AXIS, Y_AXIS, Z_AXIS
from .cmds import CMDS

from .cpnt_mesh.cm_mesh import CpntMesh

LOC_SCALE = 1.0
LOC_COL = 'red'
