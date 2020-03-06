"""Plugin which creates a custom locator node for Viewport 2.0.

The locator appears as some 2d text and some moveable 3d text.

Source:
dilenshah3d.wordpress.com/2017/01/04/viewport-2-0-and-drawing-with-opengl-in-maya
"""

import math
import sys
import time

from maya.api import OpenMaya as om, OpenMayaUI as omui, OpenMayaRender as omr

from psyhive.utils import lprint
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_unique

_NODE_NAME = 'MeshXRayer'
_NODE_ID = 0x80005

_TEXT = time.strftime('%H:%M:%S')


def maya_useNewAPI():
    """Tell maya to use maya.api.om module.

    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """


class MeshXRayer(omui.MPxLocatorNode):
    """Node implementation with standard viewport draw."""

    id = om.MTypeId(_NODE_ID)
    drawDbClassification = "drawdb/geometry/MeshXRayer"
    drawRegistrantId = _NODE_NAME+"Plugin"

    in_mesh = om.MObject()
    color = om.MObject()
    hide_angle = om.MObject()
    draw_control = om.MObject()
    draw_mesh = om.MObject()

    @staticmethod
    def creator():
        """Create node instance - executed on create node."""
        return MeshXRayer()

    @staticmethod
    def initialize():
        """Initialise node - execute on plugin initialise."""

        # Add in_mesh attr
        _attr = om.MFnTypedAttribute()
        MeshXRayer.in_mesh = _attr.create(
            'in_mesh', 'in_mesh', om.MFnNumericData.kMesh)
        _attr.writable = True
        _attr.connectable = True
        _attr.readable = False
        MeshXRayer.addAttribute(MeshXRayer.in_mesh)

        # Add color attr
        _attr = om.MFnNumericAttribute()
        MeshXRayer.color = _attr.createColor("color", "color")
        _attr.keyable = True
        _attr.connectable = True
        _attr.writable = True
        _attr.readable = True
        _attr.usedAsColor = True
        MeshXRayer.addAttribute(MeshXRayer.color)

        # Add hide angle attr
        _attr = om.MFnNumericAttribute()
        MeshXRayer.hide_angle = _attr.create(
            "hide_angle", "hide_angle", om.MFnNumericData.kFloat)
        _attr.keyable = True
        _attr.connectable = True
        _attr.writable = True
        _attr.readable = True
        _attr.setMin(0)
        _attr.setMax(180)
        _attr.default = 90
        MeshXRayer.addAttribute(MeshXRayer.hide_angle)

        # Add show control attr
        _attr = om.MFnNumericAttribute()
        MeshXRayer.draw_control = _attr.create(
            "draw_control", "draw_control", om.MFnNumericData.kBoolean)
        _attr.keyable = True
        _attr.connectable = True
        _attr.writable = True
        _attr.readable = True
        _attr.default = True
        MeshXRayer.addAttribute(MeshXRayer.draw_control)

        # Add show control attr
        _attr = om.MFnNumericAttribute()
        MeshXRayer.draw_mesh = _attr.create(
            "draw_mesh", "draw_mesh", om.MFnNumericData.kBoolean)
        _attr.keyable = True
        _attr.connectable = True
        _attr.writable = True
        _attr.readable = True
        _attr.default = True
        MeshXRayer.addAttribute(MeshXRayer.draw_mesh)

    def postConstructor(self):
        """Executed after construction is complete."""

        # Fix name
        _node = om.MFnDependencyNode(self.thisMObject())
        _node.setName(get_unique('meshXRayerShape'))


class MeshXRayerData(om.MUserData):
    """Used for caching data (?)."""

    def __init__(self):
        """Constructor."""
        super(MeshXRayerData, self).__init__(False)  # don't delete after draw

        self.mesh_tris = om.MPointArray()
        self.color = om.MColor()
        self.hide_angle = 0.0
        self.draw_control = True
        self.draw_mesh = True

        self.mesh_to_cam = om.MVector()


class MeshXRayerDrawOverride(omr.MPxDrawOverride):
    """Drawing override for MeshXRayer."""

    def __init__(self, obj):
        """Constructor.

        A drawing override is created for each instance of the node.

        Args:
            obj (MObject): object to override drawing for
        """
        super(MeshXRayerDrawOverride, self).__init__(
            obj, MeshXRayerDrawOverride.draw)

    @staticmethod
    def creator(obj):
        """Creator.

        Args:
            obj (MObject): object to override drawing for
        """
        return MeshXRayerDrawOverride(obj)

    @staticmethod
    def draw(context, data):
        """Execute on draw.

        A draw method is required for a MPxDrawOverride. It is executed
        every time the viewport updates.

        Args:
            context (MDrawContext): draw context
            data (MeshXRayerData): data being drawn
        """

    def supportedDrawAPIs(self):
        """List supported draw APIs.

        This plugin supports both GL and DX.
        """
        return (omr.MRenderer.kOpenGL |
                omr.MRenderer.kDirectX11 |
                omr.MRenderer.kOpenGLCoreProfile)

    def prepareForDraw(self, obj, cam, frame_context, data,
                       verbose=0):
        """Retrieve data cache (create if does not exist).

        Args:
            obj (MDagPath): path to object being drawn
            cam (MDagPath): path to viewport camera
            frame_context (MFrameContext): frame context
            data (MeshXRayerData): previous data
            verbose (int): print process data

        Returns:
            (MeshXRayerData): node data
        """
        lprint('PREPARE FOR DRAW', verbose=verbose)

        _data = data
        if not isinstance(_data, MeshXRayerData):
            _data = MeshXRayerData()
            lprint(' - USING EXISTING DATA', _data, verbose=verbose)
        lprint(' - DATA', _data, verbose=verbose)

        # Read in_mesh plug
        lprint(' - OBJ', obj, verbose=verbose)
        _node = obj.node()
        _in_mesh_plug = om.MPlug(_node, MeshXRayer.in_mesh)
        lprint(' - IN MESH PLUG', _in_mesh_plug, verbose=verbose)

        _data.mesh_tris.clear()
        if _in_mesh_plug.isNull:
            return None
        if _in_mesh_plug.asMDataHandle().type() != om.MFnData.kMesh:
            return None
        _in_mesh_handle = _in_mesh_plug.asMDataHandle().asMesh()
        _in_mesh = om.MFnMesh(_in_mesh_handle)

        # Read mesh triangles
        _mesh_pts = _in_mesh.getPoints()
        for _poly_id in range(_in_mesh.numPolygons):
            _vtx_ids = _in_mesh.getPolygonVertices(_poly_id)
            for _vtx_id in _vtx_ids[:3]:
                _data.mesh_tris.append(_mesh_pts[_vtx_id])
        lprint(' - IN MESH', _in_mesh, len(_in_mesh.getPoints()),
               verbose=verbose)

        # Read col/hide_angle + draw toggles
        _col_plug = om.MPlug(_node, MeshXRayer.color)
        _data.color = om.MColor([_col_plug.child(_idx).asFloat()
                                 for _idx in range(3)])
        _data.hide_angle = om.MPlug(_node, MeshXRayer.hide_angle).asFloat()
        _data.draw_control = om.MPlug(_node, MeshXRayer.draw_control).asBool()
        _data.draw_mesh = om.MPlug(_node, MeshXRayer.draw_mesh).asBool()

        _obj_pos = hom.HMatrix(obj.inclusiveMatrix()).pos()
        _cam_pos = hom.HMatrix(cam.inclusiveMatrix()).pos()
        _data.mesh_to_cam = _cam_pos - _obj_pos

        return _data

    def hasUIDrawables(self):
        """Test if this drawing override has drawables.

        Returns:
            (bool): true
        """
        return True

    def addUIDrawables(self, obj, painter, frame_context, data):
        """Add drawables - viewport 2.0 draw function.

        Executed on viewport update. Not sure why drawing happens here and
        not in draw function.

        Args:
            obj (MDagPath): path to object being drawn
            painter (MUIDrawManager): draw manager
            frame_context (MFrameContext): frame context
            data (MeshXRayerData): node data
        """
        if not isinstance(data, MeshXRayerData):
            return

        painter.beginDrawable()

        _angle_to_cam = math.degrees(data.mesh_to_cam.angle(hom.Z_AXIS))
        _hide_angle = data.hide_angle
        _hide_angle_r = math.radians(_hide_angle)

        # Draw polys over mesh
        if data.draw_mesh and _angle_to_cam <= _hide_angle:
            painter.beginDrawInXray()
            painter.setColor(data.color)
            painter.mesh(omr.MGeometry.kTriangles, data.mesh_tris)
            painter.endDrawInXray()

        # Draw control
        if data.draw_control:
            _rad = 2.0
            painter.setColor(hom.get_col('red'))
            painter.circle(hom.ORIGIN, hom.Y_AXIS, _rad)
            _end = hom.HPoint(0, 0, _rad*1.2)
            painter.line(hom.ORIGIN, _end)
            painter.cone(_end, hom.Z_AXIS, 0.2, 0.4)
            for _x_mult in [1, -1]:
                _x_cpnt = _x_mult*_rad*math.sin(_hide_angle_r)
                _z_cpnt = _rad*math.cos(_hide_angle_r)
                _pt = hom.HPoint(_x_cpnt, 0, _z_cpnt)
                painter.line(hom.ORIGIN, _pt)

        painter.endDrawable()


def initializePlugin(obj):
    """Standard plugin load function.

    Args:
        obj (MObject): plugin object (?)
    """
    _plugin = om.MFnPlugin(obj, "Henry van der Beek", "1.0", "Any")

    try:
        _plugin.registerNode(
            _NODE_NAME,
            MeshXRayer.id,
            MeshXRayer.creator,
            MeshXRayer.initialize,
            om.MPxNode.kLocatorNode,
            MeshXRayer.drawDbClassification)
    except Exception:
        sys.stderr.write("Failed to register node\n")
        raise

    try:
        omr.MDrawRegistry.registerDrawOverrideCreator(
            MeshXRayer.drawDbClassification,
            MeshXRayer.drawRegistrantId,
            MeshXRayerDrawOverride.creator)
    except Exception:
        sys.stderr.write("Failed to register override\n")
        raise


def uninitializePlugin(obj):
    """Standard plugin unload function.

    Args:
        obj (MObject): plugin object (?)
    """
    _plugin = om.MFnPlugin(obj)

    try:
        _plugin.deregisterNode(MeshXRayer.id)
    except Exception:
        sys.stderr.write("Failed to deregister node\n")

    try:
        omr.MDrawRegistry.deregisterDrawOverrideCreator(
            MeshXRayer.drawDbClassification,
            MeshXRayer.drawRegistrantId)
    except Exception:
        sys.stderr.write("Failed to deregister override\n")
