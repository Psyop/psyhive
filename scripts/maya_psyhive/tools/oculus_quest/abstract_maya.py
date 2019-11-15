import functools
import imath
import inspect
import math
import pprint
import numpy
import os
import re
import subprocess
import shutil
import sys
import tempfile
import time


import mtoa
from maya import cmds, mel
from maya import OpenMaya as om

from psyhive import qt
from psyhive.qt import QtCore
from psyhive.utils import dprint, File, abs_path, test_path
from maya_psyhive.utils import get_shp, load_plugin


def keep_selection(func):
    def _keep_selection_func(*args, **kwargs):
        old_selection = cmds.ls(selection=True, long=True)
        result = func(*args, **kwargs)
        old_selection = cmds.ls(old_selection, long=True)
        if old_selection:
            cmds.select(old_selection)
        else:
            cmds.select(clear=True)
        return result
    return _keep_selection_func


def time_operation(func):
    @functools.wraps(func)
    def _time_operation_func(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        delta = time.time() - start
        sys.stdout.write("{}: {} seconds\n".format(func, delta))
        return result
    return _time_operation_func


def keep_selection_mode(func):
    """
    Decorator - turn off Maya display while func is running.
    if func will fail, the error will be raised after.
    """

    @functools.wraps(func)
    def _keep_selection_mode_func(*args, **kwargs):

        # Turn full screen on:
        _c = cmds.selectMode(q=True, component=True)
        _o = cmds.selectMode(q=True, object=True)

        # Decorator will try/except running the function.
        # But it will always turn fullscreen at the end.
        # In case the function failed, it will prevent leaving maya in fullscreen mode.
        try:
            return func(*args, **kwargs)
        except Exception:
            raise  # will raise original error
        finally:
            cmds.selectMode(object=_o, component=_c)

    return _keep_selection_mode_func


def print_func_name(func):
    """
    Decorator - Print the wrapped func name.
    """

    @functools.wraps(func)
    def _print_name_func(*args, **kwargs):
        # Print the wrapped funcname
        print "{::^80}:".format(" {} ".format(func.__name__.upper()))

        # Decorator will try/except running the function.
        # But it will always return en the end.
        try:
            return func(*args, **kwargs)
        except Exception:
            raise  # will raise original error
        finally:
            print "{::^80}:".format(" {} COMPLETE ".format(func.__name__.upper()))

    return _print_name_func


def keep_current_camera(func):
    """
    Decorator - turn off Maya display while func is running.
    if func will fail, the error will be raised after.
    """

    @functools.wraps(func)
    def _keep_camera_func(*args, **kwargs):

        active_view = get_active_viewport()
        active_camera = get_active_camera()

        # Decorator will try/except running the function.
        # But it will always turn fullscreen at the end.
        # In case the function failed, it will prevent leaving maya in fullscreen mode.
        try:
            return func(*args, **kwargs)
        except Exception:
            raise  # will raise original error
        finally:
            cmds.modelEditor(active_view, camera=active_camera, edit=True)

    return _keep_camera_func


def fullscreen_on(func):
    """
    Decorator - turn off Maya display while func is running.
    if func will fail, the error will be raised after.
    """

    @functools.wraps(func)
    def wrap(*args, **kwargs):

        # Turn full screen on:
        full_screen_on()

        # Decorator will try/except running the function.
        # But it will always turn fullscreen at the end.
        # In case the function failed, it will prevent leaving maya in fullscreen mode.
        try:
            return func(*args, **kwargs)
        except Exception:
            raise  # will raise original error
        finally:
            full_screen_off()

    return wrap


def viewport_off(func):
    """
    Decorator - turn off Maya display while func is running.
    if func will fail, the error will be raised after.
    """

    @functools.wraps(func)
    def wrap(*args, **kwargs):

        # Turn $gMainPane Off:
        mel.eval("paneLayout -e -manage false $gMainPane")

        # Decorator will try/except running the function.
        # But it will always turn on the viewport at the end.
        # In case the function failed, it will prevent leaving maya viewport off.
        try:
            return func(*args, **kwargs)
        except Exception:
            raise  # will raise original error
        finally:
            mel.eval("paneLayout -e -manage true $gMainPane")

    return wrap
##### END DECORATOR #####


def set_fps(fps):
    """Set the maya frames per second

    Args:
        fps (str): Maya fps input string.  e.g.: "75fps".  This is annoying and should probably become an int

    Returns:
        None
    """
    current_unit = cmds.currentUnit(q=True, time=True)
    if current_unit != fps:
        cmds.currentUnit(time=fps)


def set_frame_range_to_anim_extent():
    """Find all animation curves in the scene and set maya's first and last frames to that range.

    Returns:
        None
    """
    start = sys.maxsize
    end = -sys.maxsize
    anim_curves = cmds.ls(type=['animCurveTA', 'animCurveTL', 'animCurveTT', 'animCurveTU'])
    for each_curve in anim_curves:
        last = int(cmds.keyframe(each_curve, q=1, keyframeCount=1))
        if last > 0:
            keys = cmds.keyframe(each_curve, q=1, index=(0, last-1), tc=1)
            for key in keys:
                end = max(key, end)
                start = min(key, start)
    if start != sys.maxsize:
        cmds.playbackOptions(min=start, max=end, ast=start, aet=end)


def set_outliner_order(order_list):
    """
    Reorders top nodes in the Maya outliner to match the input "order_list".  This always puts the maya cameras at
    the top.

    Args:
        order_list (list):  List of maya top nodes to order, from top to bottom.

    Returns:
        None
    """
    top_maya_nodes = [
            "|persp",
            "|top",
            "|front",
            "|side",
        ]
    assemblies = cmds.ls(assemblies=True, l=True)
    order_list = top_maya_nodes + order_list
    order_list.reverse()

    for name in order_list:
        if not name.startswith("|"):
            name = "|"+name
        if cmds.objExists(name):
            cmds.reorder(name, front=True)


def parent_node(node, parent):
    try:
        cmds.parent(node, parent)
    except:
        pass


def create_node_hierarchy(node_parent_list):
    """
    Given a list with
    Args:
        node_parent_list (list): List of node and parent pairs, e.g. [[node, parent], [node, parent], ...]].  If
        parent is None then leaves at world level

    Returns:
        None
    """
    for [name, parent] in node_parent_list:
        if not cmds.objExists(name):
            cmds.group(name=name, empty=True)
            if parent != None:
                cmds.parent(name, parent)


def create_camera(name, focal_length=35, translation=None, rotation=None, lock_translation=False, force=True,
                  parent=None, horizontal_aperture=None, vertical_aperture=None, film_fit="vertical",
                  locator_scale=None, near_clip=None, far_clip=None):
    """
    Create a maya camera
    Args:
        name (str): The name of the camera transform node.
        focal_length (float): Focal length of the camera in mm
        translation (list): list triple of tx, ty, tz (e.g. [0, 5, 0])
        rotation (list): list triple of rx, ry, rz (e.g. [0, 45, 0])
        lock_translation (bool): Specify whether the translation channels should be locked after the initial position
        force (bool): Deletes the name if it already exists

    Returns:
        str: Camera name on success, None if not created.
    """
    if cmds.objExists(name) and force:
        cmds.delete(name)
    elif not force:
        return
    new_name = cmds.camera(name=name, focalLength=focal_length)[0]
    if new_name != name:
        cmds.rename(new_name, name)
    if horizontal_aperture != None:
        cmds.setAttr("{}.horizontalFilmAperture".format(name), horizontal_aperture)
    if vertical_aperture != None:
        cmds.setAttr("{}.verticalFilmAperture".format(name), vertical_aperture)
    if film_fit != None:
        fit_dict = {"fill":0, "horizontal":1, "vertical":2, "overscan":3}
        if film_fit in fit_dict:
            cmds.setAttr("{}.filmFit".format(name), fit_dict.get(film_fit))
    if rotation != None:
        cmds.xform(name, rotation=rotation, a=True)
    if translation != None:
        cmds.xform(name, translation=translation, a=True)
    if far_clip != None:
        cmds.setAttr("{}.farClipPlane".format(name), far_clip)
    if near_clip != None:
        cmds.setAttr("{}.nearClipPlane".format(name), near_clip)
    if locator_scale != None:
        cmds.setAttr("{}.locatorScale".format(name), locator_scale)
    cmds.xform(name, scale=[10, 10, 10], a=True)
    if lock_translation:
        cmds.setAttr("{}.tx".format(name), lock=True)
        cmds.setAttr("{}.ty".format(name), lock=True)
        cmds.setAttr("{}.tz".format(name), lock=True)
    if parent:
        if not cmds.objExists(parent):
            cmds.group(name=group, empty=True)
            cmds.parent(name, group)
    return name


def create_group(name, parent=None, force=True):
    """
    Create an empty maya group with the given name

    Args:
        name (str): Name for the new node
        parent (str): Optional parent for the new node
        force (bool): Whether to force creation.  If True, delete any node that has the same name first

    Returns:
        str: node name
    """
    if force and cmds.objExists(name):
        cmds.delete(name)
    cmds.group(name=name, empty=True)
    if parent:
        cmds.parent(name, parent)
    return name


def lock_transformations(node, unlock=False):
    """
    Lock all transformations for the current node
    Args:
        node (str): name of the node to unlock
        unlock (bool): Whether to unlock instead of locking the attributes

    Returns:
        None
    """
    cmds.setAttr("{}.tx".format(node), lock=unlock)
    cmds.setAttr("{}.ty".format(node), lock=unlock)
    cmds.setAttr("{}.tz".format(node), lock=unlock)
    cmds.setAttr("{}.rx".format(node), lock=unlock)
    cmds.setAttr("{}.ry".format(node), lock=unlock)
    cmds.setAttr("{}.rz".format(node), lock=unlock)
    cmds.setAttr("{}.sx".format(node), lock=unlock)
    cmds.setAttr("{}.sy".format(node), lock=unlock)
    cmds.setAttr("{}.sz".format(node), lock=unlock)


def is_backfacing(face, face_normal, viewpoint):
    """
    Identify if an individual face is backfacing from the current viewpoint.

    Args:
        face (str): Name of the face to check
        face_normal (imath.V3f): Normal of the face
        viewpoint (imath.V3f): Point from which to view the normal

    Returns:
        bool: True if backfacing, False if facing camera
    """
    face_position = cmds.xform(face, ws=True, q=True, translation=True)
    face_position = imath.V3f(face_position[0], face_position[1], face_position[2])
    look_vector = face_position - viewpoint

    if face_normal.dot(look_vector) < 0:
        return False
    else:
        return True


def get_face_normals_for_object(node):
    """
    Get a list of all face normals for an object
    Args:
        node (str): Node name for which to get all face normals.

    Returns:
        dict: Dictionary of the face normals, where key is the face and value is an imath.V3f of the vector.
    """
    face_normal_dict = {}
    face_normals = cmds.polyInfo(node, faceNormals=True)
    node = node[0].split(".")[0]
    re_compile = re.compile("FACE_NORMAL\s+(?P<id>[0-9]+):\s(?P<x>-?[0-9]+\.[0-9]+)\s(?P<y>-?[0-9]+\.[0-9]+)\s(?P<z>-?[0-9]+\.[0-9]+)\n")
    for normal in face_normals:
        match = re_compile.match(normal)
        if match:
            id = match.group("id")
            x = float(match.group("x"))
            y = float(match.group("y"))
            z = float(match.group("z"))
            key = "{}.f[{}]".format(node, id)
            face_normal_dict[key] = imath.V3f(x, y, z)
    print face_normal_dict
    return face_normal_dict


def get_back_faces(node, view_point, front_faces=False, recurse=True):
    """
    Given a node, recursively get a list of all faces whose backs are visible from a view point
    Args:
        node (str): Name of the maya node to check
        view_point (imath.V3f): Input view point position
        recurse (bool): Whether to recursively search from the top node.  Default is True.

    Returns:
        list: All back faces
    """
    if recurse:
        nodes = cmds.ls(node, dag=True, type="mesh", l=True, noIntermediate=True)
    else:
        nodes = [node]
    all_back_faces = []
    for node in nodes:
        face_normal_dict = get_face_normals_for_object(node)
        for face, normal in face_normal_dict.iteritems():
            if not front_faces:
                if is_backfacing(face, normal, view_point):
                    all_back_faces.append(face)
            elif front_faces:
                if not is_backfacing(face, normal, view_point):
                    all_back_faces.append(face)
    return all_back_faces


def create_bbox(name, width, height, depth, translation=None, force=True):
    """
    Create a templated bounding box with bottom on the ground.  "translation" is applied on top.
    Args:
        name (str): name of the bounding box
        width (float): width in maya units
        height (float): height in maya units
        depth (float): depth in maya units
        translation (list): Translation to apply on top of the bounding box
        force (bool): Delete the bbox if it already exists.  Default is True

    Returns:
        str: name of the bbox if successful, None otherwise
    """
    print 'CREATE BBOX', width, height, depth
    if cmds.objExists(name):
        if force:
            cmds.delete(name)
        else:
            return
    cmds.polyCube(constructionHistory=False, n=name, w=width, h=height, d=depth)
    cmds.setAttr("{}.template".format(name), True)
    cmds.xform(name, t=[0, height*0.5, 0])
    if translation != None:
        cmds.xform(name, translation=translation, worldSpace=True, relative=True)
    freeze_transformations(name)
    return name


def get_bbox_corners(node):
    """
    Get the for corner points for the bounding box of a given node

    Args:
        node: Name of the node to query

    Returns:
        list: List of imath.V3f points from the bounding box corners

    """
    bbox = cmds.exactWorldBoundingBox(node)
    point_list = []
    [xmin, ymin, zmin, xmax, ymax, zmax] = bbox

    point_list.append(imath.V3f(xmin, ymin, zmin))
    point_list.append(imath.V3f(xmin, ymin, zmax))
    point_list.append(imath.V3f(xmin, ymax, zmin))
    point_list.append(imath.V3f(xmin, ymax, zmax))
    point_list.append(imath.V3f(xmax, ymin, zmin))
    point_list.append(imath.V3f(xmax, ymin, zmax))
    point_list.append(imath.V3f(xmax, ymax, zmin))
    point_list.append(imath.V3f(xmax, ymax, zmax))

    return point_list


def get_node_center(node):
    """
    Return the center of a node by finding the middle of its bounding box

    Args:
        node (str): the maya node name

    Returns:
        imath.V3f: position of the maya node

    """
    bbox = cmds.xform(node, q=True, bb=True, ws=True)
    x = (bbox[0] + bbox[3]) * 0.5
    y = (bbox[1] + bbox[4]) * 0.5
    z = (bbox[2] + bbox[5]) * 0.5
    return imath.V3f(x, y, z)


def get_world_space_area(node):
    """
    Get world space area for given node
    Args:
        node (str): maya node

    Returns:
        float: World space area

    """
    area = cmds.polyEvaluate(node, worldArea=True)
    return area


def get_uv_area(node):
    """
    Get UV area of a given node.

    Args:
        node (str): Name of the maya node

    Returns:
        float: Total UV area of the input node

    """
    try:
        sList = om.MSelectionList()
        sList.add(node)
        sIter = om.MItSelectionList(sList)
        dagp = om.MDagPath()
        mobj = om.MObject()
        sIter.getDagPath(dagp, mobj)
        pIter = om.MItMeshPolygon(dagp)
        areaParam = om.MScriptUtil()
        areaParam.createFromDouble(0.0)
        areaPtr = areaParam.asDoublePtr()
        totalArea = 0
        while not pIter.isDone():
            pIter.getUVArea(areaPtr)
            area = om.MScriptUtil(areaPtr).asDouble()
            totalArea += area
            pIter.next()
        return totalArea
    except:
        raise Exception("Object is invalid! {}".format(node))


def unfold_uvs(nodes):
    """
    Unfold a list of nodes in UV space

    Args:
        nodes (list): List of maya nodes

    Returns:
        None

    """
    inc = 100
    i = 0
    while 1:
        if i < len(nodes):
            short_nodes = nodes[i:i+inc]
        else:
            short_nodes = nodes[i:len(nodes)]
        cmds.unfold(short_nodes)
        if i > len(nodes):
            break
        i += 100


def calculate_texel_density(faces, resolution):
    """
    Calculates the world space texel density for the input faces

    Args:
        faces (list): list of input faces
        resolution (int): Resolution of the output baked texture

    Returns:
        float: texel density
    """
    faces = cmds.filterExpand(faces, ex=False, sm=34)
    area_3d = sum(cmds.polyEvaluate(faces, worldFaceArea=True))
    area_2d = sum(cmds.polyEvaluate(faces, uvFaceArea=True))
    return (math.sqrt(area_2d) / math.sqrt(area_3d)) * resolution


@keep_selection
def set_world_space_texel_density(nodes, density, texture_resolution):
    """
    Set the World space texel density

    Args:
        nodes (list): List of input nodes
        density (float): texel density multiplier
        texture_resolution (int): size of the output texture to determine texels

    Returns:
        None
    """
    shell_list = get_uv_shells(nodes)
    for uv_shell in shell_list:
        selection_faces = cmds.polyListComponentConversion(uv_shell, toFace=True)
        selection_faces = cmds.filterExpand(selection_faces, ex=False, sm=34)
        current_density = calculate_texel_density(selection_faces, texture_resolution)
        if current_density:
            scale = density / current_density
            ((umin, umax), (vmin, vmax)) = cmds.polyEvaluate(uv_shell, boundingBoxComponent2d=True)
            pivot_u = (umin + umax) * 0.5
            pivot_v = (vmin + vmax) * 0.5
            cmds.polyEditUV(uv_shell, pivotU=pivot_u, pivotV=pivot_v, scaleU=scale, scaleV=scale)


@time_operation
def get_uv_shells(nodes):
    """
    Given a list of maya nodes, find all mesh children and return the list of shell IDs

    Args:
        nodes:

    Returns:

    """
    meshes = get_mesh_children(nodes)
    result = []
    for mesh in meshes:
        cmds.select("{}.f[*]".format(mesh))
        # This gets the UV shell IDs, e.g.: [0, 1, 2, 3]
        shell_list = cmds.polyEvaluate(mesh, activeUVShells=True)
        for shell in shell_list:
            result.append(cmds.polyEvaluate(mesh, uvsInShell=shell))
    return result


####### EXPERIMENTAL ########
@time_operation
def get_face_list_for_shells(shells):
    # faces = [cmds.polyListComponentConversion(shell, toFace=True) for shell in shells]
    # return faces
    faces = []
    for shell in qt.progress_bar(shells, 'Reading {:d} shell{}'):
        faces.append(cmds.polyListComponentConversion(shell, toFace=True))
    return faces

def get_uv_area_for_faces(faces):
    uv_area_list = [sum(cmds.polyEvaluate(face, uvFaceArea=True)) for face in faces]
    return uv_area_list

def get_uv_bbox_area_for_shells(shells):
    uv_bbox_area_list = []
    for shell in shells:
        ((umin, umax), (vmin, vmax)) = cmds.polyEvaluate(shell, boundingBoxComponent2d=True)
        area = (vmax - vmin) * (umax - umin)
        uv_bbox_area_list.append(area)
    return uv_bbox_area_list


@time_operation
def get_world_space_area_for_faces(faces):
    # area_3d_list = [sum(cmds.polyEvaluate(face, worldFaceArea=True)) for face in faces]
    # return area_3d_list
    area_3d_list = []
    for face in qt.progress_bar(faces, 'Reading {:d} face{}'):
        _area = sum(cmds.polyEvaluate(face, worldFaceArea=True))
        area_3d_list.append(_area)
    return area_3d_list

@time_operation
def get_distance_for_faces(faces, viewpoint):
    object_distance_dict = {}
    face_center_list = [get_node_center(face) for face in faces]
    face_center_distance_list = [(viewpoint - face_center).length() for face_center in face_center_list]
    node_names = [face[0].split(".")[0] for face in faces]
    for node in set(node_names):
        closest_point = get_closest_point([viewpoint[0], viewpoint[1], viewpoint[2]], node)[0]
        distance = (viewpoint - imath.V3f(*closest_point)).length()
        object_distance_dict[node] = distance

    distance_list = []
    # The center of faces for a sphere would be the center, so to get around that problem we're taking the max
    # between that center and the closest measured point from the surface.  That will avoid an environment dome
    # appearing like it's at the origin.
    for i, face_list in enumerate(faces):
        node = face_list[0].split(".")[0]
        distance_list.append(max(object_distance_dict.get(node), face_center_distance_list[i]))
    return distance_list

def auto_uv_object(node):
    cmds.polyAutoProjection(node, constructionHistory=0, lm=0, pb=0, ibd=1, cm=0, l=2, sc=1, o=1, p=6, ps=0.2, ws=0)


def create_spherical_uvs(top_node, center, rotation=None):
    nodes = get_mesh_children(top_node)
    nodes = ["{}.f[*]".format(n) for n in nodes]
    kwargs = dict()
    if rotation:
        kwargs["rx"] = rotation[0]
        kwargs["ry"] = rotation[1]
        kwargs["rz"] = rotation[2]
    uv_projects = cmds.polyProjection(nodes, ch=1, type="Spherical", insertBeforeDeformers=1, smartFit=0, pcx=center[0],
                                     pcy=center[1], pcz=center[2], **kwargs)
    if not uv_projects:
        raise Exception("Could not project onto nodes under '{}'".format(top_node))

    for uv_project in uv_projects:
        cmds.setAttr("{}.projectionHorizontalSweep".format(uv_project), 1.8)
        cmds.setAttr("{}.projectionVerticalSweep".format(uv_project), 1.8)


def create_projection_uvs(top_node, point):
    # create new projection camera
    camera = "projection_cam"
    aim_locator = "projection_cam_aim"
    create_camera(camera, focal_length=12, translation=point, lock_translation=True)
    set_viewport_camera(camera)
    loc = cmds.spaceLocator()[0]
    if cmds.objExists(aim_locator):
        cmds.delete(aim_locator)
    cmds.rename(loc, aim_locator)
    cmds.aimConstraint(aim_locator, camera, offset=[0, 0, 0], weight=1, aimVector=[0, 0, -1], upVector=[0, 1, 0],
                       worldUpType="vector", worldUpVector=[0, 1, 0])

    # Get list of shells
    nodes = get_mesh_children(top_node)
    uv_shells = get_uv_shells(nodes)
    faces_list = get_face_list_for_shells(uv_shells)

    for faces in qt.progress_bar(faces_list, 'Reading {:d} faces'):
        back_faces = get_back_faces(faces, point, recurse=False)
        front_faces = get_back_faces(faces, point, front_faces=True, recurse=False)
        for faces in [back_faces, front_faces]:
            if not faces:
                continue
            node = faces[0].split(".")[0]
            cmds.select(faces)
            isolate_in_viewport(node)
            # find the center of its bounding box in world space
            center = get_node_center(faces)
            # look at the point with the camera
            cmds.xform(aim_locator, t=center, a=True)
            get_faces_from_screen()
            cmds.polyProjection(faces, mapDirection="p", type="Planar")
            # run unfold

@time_operation
def find_faces_with_no_uvs(nodes, uv_threshold=0.00000000001):
    cmds.select(nodes)
    cmds.polySelectConstraint(mode=3, type=8, geometricarea=1, geometricareabound=(0.0, 1000000.0))
    cmds.polySelectConstraint(mode=3, type=8, texturedarea=1, texturedareabound=(0, uv_threshold))
    selected = cmds.ls(sl=True, l=True)
    cmds.polySelectConstraint(mode=0, type=8, texturedarea=0, geometricarea=0)
    return selected

@keep_selection
@time_operation
def auto_uv_faces_with_no_uvs(nodes):
    faces = find_faces_with_no_uvs(nodes)
    node_dict = {}
    for face in faces:
        node = face.split(".")[0]
        if not node in node_dict:
            node_dict[node] = []
        node_dict[node].append(face)
    cmds.select(clear=True)
    for key, value in node_dict.iteritems():
        cmds.select(value, add=True)
        auto_uv_object(value)

@keep_selection
@time_operation
def set_relative_texel_density(nodes, viewpoint, density, scale_clamp=1.0, distance_clamp=0):
    """
    Set the UVs to be based off of a relative viewpoint
    Args:
        nodes (list): List of nodes to affect
        viewpoint (list): translation representing a viewpoint, [x, y, z]
        density (float): Density of pixels relative to the world space geo

    Returns:
        None
    """
    print 'VIEWPOINT'
    viewpoint = imath.V3f(*viewpoint)
    print 'AUTO UV FACES WITH NO UVS'
    auto_uv_faces_with_no_uvs(nodes)
    print 'GET UV SHELLS'
    uv_shells = get_uv_shells(nodes)
    print 'GET FACE LIST FOR SHELLS'
    faces = get_face_list_for_shells(uv_shells)
    print 'GET UV AREA FOR FACES'
    uv_area_list = get_uv_area_for_faces(faces)
    print 'GET UV BBOX FOR SHELLS'
    uv_bbox_area_list = get_uv_bbox_area_for_shells(uv_shells)

    area_3d_list = get_world_space_area_for_faces(faces)
    shell_distance_list = get_distance_for_faces(faces, viewpoint)

    unfold_threshold = .1
    # If ratio is bad or UV bbox has a huge disparity between w/h.  for now try the UV bbox ratio
    shells_for_unfold_i = [i for i in range(0, len(uv_area_list)) if uv_bbox_area_list[i] and uv_area_list[i] /
                                                                         uv_bbox_area_list[i] < unfold_threshold]
    for i in shells_for_unfold_i:
        unfold_uvs(uv_shells[i])
        uv_area_list[i] = get_uv_area_for_faces([faces[i]])[0]
        uv_bbox_area_list[i] = get_uv_bbox_area_for_shells([uv_shells[i]])[0]

    multiplier_list = []
    for i, distance in enumerate(shell_distance_list):
        if distance <= distance_clamp:
            falloff_multiplier = scale_clamp
        else:
            falloff_multiplier = min(1.0 / (distance - distance_clamp), scale_clamp)
        screen_area = falloff_multiplier * math.sqrt(area_3d_list[i]) * 0.01 * density
        if uv_area_list[i]:
            scale = screen_area / math.sqrt(uv_area_list[i])
        else:
            scale = 1
            print "Zero UV area for '{}'".format(faces)
        multiplier_list.append(scale)

    [cmds.polyEditUV(uv_shells[i], pu=0.5, pv=0.5, sv=multiplier_list[i], su=multiplier_list[i]) for i in range(0, len(multiplier_list))]

####### END EXPERIMENTAL ########


def hide_object(node):
    """Hide the given node"""
    cmds.setAttr("{}.visibility".format(node), 0)


def triangulate_objects(nodes):
    """
    Triangulates a list of nodes

    Args:
        nodes (list): List of maya nodes

    Returns:
        None
    """
    nodes = get_mesh_children(nodes)
    nodes = [node for node in nodes if not cmds.ls((cmds.listHistory(node) or []), type="polyTriangulate")]
    for node in nodes:
        cmds.polyTriangulate(node, ch=0)


def create_material_network(basename, texture_name, assign_to=None):
    """
    Create a simple material network with a texture node and a material and optionally assign to something

    Args:
        basename:
        texture_name:
        assign_to:

    Returns:
        str: Shading Node
    """
    material_node = "baked_lambert_"+basename
    texture_node = "baked_texture_"+basename
    placement_node = "baked_placement_"+basename
    shading_group = material_node + "SG"

    for node in [material_node, texture_node, placement_node]:
        if cmds.objExists(node):
            cmds.delete(node)

    cmds.shadingNode("lambert", asShader=True, name=material_node)
    cmds.shadingNode("file", asTexture=True, name=texture_node)
    cmds.shadingNode("place2dTexture", asUtility=True, name=placement_node)
    if not cmds.objExists(shading_group):
        cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shading_group)
    try:
        cmds.connectAttr("{}.outUV".format(placement_node), "{}.uv".format(texture_node))
        cmds.connectAttr("{}.outUvFilterSize".format(placement_node), "{}.uvFilterSize".format(texture_node))
        cmds.connectAttr("{}.outColor".format(texture_node), "{}.color".format(material_node), force=True)
        cmds.connectAttr("{}.outColor".format(material_node), "{}.surfaceShader".format(shading_group), force=True)
    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")

        print "SHADER CONNECTION ERROR: ", re


    cmds.setAttr("{}.fileTextureName".format(texture_node), texture_name, type="string")
    if texture_name.endswith("exr"):
        cmds.setAttr("{}.colorSpace".format(texture_node), "Raw", type="string")

    if assign_to != None and cmds.objExists(assign_to):
        cmds.sets(assign_to, e=True, forceElement=shading_group)
    return shading_group


def calculate_texel_scale(view_point, target_point, distance_clamp=0):
    """
    Calculate a scale ratio for a target point from a view point.
    Args:
        view_point (imath.V3f): point from which to view
        target_point (imath.V3f): point that's being viewed

    Returns:
        None
    """
    distance = (view_point - target_point).length()
    # scale at 1 unit will be 1.0.  Everything after will falloff.
    scale_clamp = 1.0
    if distance <= distance_clamp:
        texel_scale = scale_clamp
    else:
        texel_scale = min(1 / (distance - distance_clamp), scale_clamp)

    return texel_scale


def scale_texture_density_for_view_points(nodes, center):
    """
    For a list of input nodes, scale the texture density
    Args:
        nodes (list): maya nodes

    Returns:
        None
    """
    origin = imath.V3f(*center)
    for node in nodes:
        # TODO: find UV shells and positions instead of nodes
        position = get_node_center(node)
        scale = calculate_texel_scale(origin, position)
        try:
            cmds.polyEditUV("{}.map[*]".format(node), pu=0.5, pv=0.5, sv=scale, su=scale)
        except:
            print "No UVs for node '{}' ...".format(node)


def get_mesh_children(node, sel=False):
    """
    Based on a top node, recursively find the parents of all mesh nodes that are children
    Args:
        node (str): Maya input node

    Returns:
        list: all transforms for mesh children
    """
    nodes = cmds.ls(node, dag=True, long=True, type="mesh", noIntermediate=True)
    nodes = cmds.listRelatives(nodes, parent=True, fullPath=True) or []
    if sel:
        cmds.select(nodes, add=True)

    return nodes


@keep_selection
def delete_history(node, nondeformer_only=True, recursive=True):
    """
    Delete history

    Args:
        node (str): Maya node
        nondeformer_only (bool): Set to only delete non-deformer history.  This will preserve animation

    Returns:
        None
    """
    if recursive:
        node = get_mesh_children(node)
    if node:
        cmds.select(node, hi=True)
        if nondeformer_only:
            mel.eval('doBakeNonDefHistory( 1, {"prePost" });')
        else:
            cmds.delete(node, hierarchy="below", constructionHistory=True)


def freeze_transformations(node, recursive=True):
    """
    Freeze transformations

    Args:
        node (str): Input maya node

    Returns:
        None
    """
    if recursive:
        node = get_mesh_children(node)
    cmds.makeIdentity(node, apply=True, t=True, r=True, s=True, n=0, pn=True)


def get_skin_clusters(node):
    """
    Get a list of skin clusters in the given node
    Args:
        node (str): input maya node

    Returns:
        list: cluster list
    """
    meshes = cmds.ls(node, dag=True, type="mesh", noIntermediate=True, long=True)
    if meshes:
        history = cmds.listHistory(meshes)
        clusters = cmds.ls(history, type="skinCluster", l=True)
    else:
        clusters = []
    return clusters


def disable_skin_clusters(node):
    """
    Disable all skin clusters under the given node

    Args:
        node (str): input maya node

    Returns:
        None
    """
    clusters = get_skin_clusters(node)
    for c in clusters:
        cmds.setAttr("{}.envelope".format(c), 0)


def enable_skin_clusters(node):
    """
    Enable all skin clusters under the given node
    Args:
        node (str): input maya node

    Returns:
        None
    """
    clusters = get_skin_clusters(node)
    for c in clusters:
        cmds.setAttr("{}.envelope".format(c), 1)


@print_func_name
def create_checker_material(checker_repeat=20):
    """
    Creates a checker material network
    Args:
        checker_repeat (int): UV repeat

    Returns:
        str: shading group for the checker material network
    """
    material_node = "checker_lambert"
    texture_node = "checker_texture"
    placement_node = "checker_2d_placement"
    shading_group = material_node + "SG"
    for node in [material_node, texture_node, placement_node]:
        if cmds.objExists(node):
            cmds.delete(node)

    cmds.shadingNode("lambert", asShader=True, name=material_node)
    cmds.shadingNode("checker", asTexture=True, name=texture_node)
    cmds.shadingNode("place2dTexture", asUtility=True, name=placement_node)
    cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shading_group)

    try:
        cmds.connectAttr("{}.outUV".format(placement_node), "{}.uv".format(texture_node))
        cmds.connectAttr("{}.outUvFilterSize".format(placement_node), "{}.uvFilterSize".format(texture_node))
        cmds.connectAttr("{}.outColor".format(texture_node), "{}.color".format(material_node), force=True)
        cmds.connectAttr("{}.outColor".format(material_node), "{}.surfaceShader".format(shading_group), force=True)
    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    cmds.setAttr("{}.repeatU".format(placement_node), checker_repeat)
    cmds.setAttr("{}.repeatV".format(placement_node), checker_repeat)

    return shading_group


@print_func_name
def create_mipmap_debug_material():
    mipmap_texture = "//coppi/glob/la/textures/mipmap_test/debug7.exr"

    material_node = "mipmap_material"
    texture_node = "mipmap_texture"
    placement_node = "mipmap_2d_placement"
    shading_group = material_node + "SG"
    for node in [material_node, texture_node, placement_node]:
        if cmds.objExists(node):
            cmds.delete(node)

    cmds.shadingNode("lambert", asShader=True, name=material_node)
    cmds.shadingNode("file", asTexture=True, name=texture_node)
    cmds.shadingNode("place2dTexture", asUtility=True, name=placement_node)
    cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shading_group)

    try:
        cmds.connectAttr("{}.outUV".format(placement_node), "{}.uv".format(texture_node))
        cmds.connectAttr("{}.outUvFilterSize".format(placement_node), "{}.uvFilterSize".format(texture_node))
        #cmds.connectAttr("{}.outColor".format(texture_node), "{}.color".format(material_node), force=True)
        cmds.setAttr("{}.color".format(material_node), 0, 0, 0, type="double3")
        cmds.connectAttr("{}.outColor".format(texture_node), "{}.incandescence".format(material_node), force=True)
        cmds.connectAttr("{}.outColor".format(material_node), "{}.surfaceShader".format(shading_group), force=True)

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    cmds.setAttr("{}.fileTextureName".format(texture_node), mipmap_texture, type="string")

    return shading_group


def assign_checker_material(node):
    """
    Assign checker material to a given node
    Args:
        node (str): Input maya node

    Returns:
        None
    """
    shading_group = create_checker_material()
    cmds.sets(node, e=True, forceElement=shading_group)

def assign_mipmap_debug_material(node):
    shading_group = create_mipmap_debug_material()
    cmds.sets(node, e=True, forceElement=shading_group)


def get_camera_fov(node):
    """
    Get the fov of the given camera in degrees
    Args:
        node:

    Returns:

    """
    # get fov in mm
    focal_length_mm = cmds.getAttr("{}.focalLength".format(node))
    camera_aperture_mm = cmds.getAttr("{}.verticalFilmAperture".format(node)) * 25.4
    fov_radians = 2. * math.atan2(camera_aperture_mm * 0.5, focal_length_mm)
    fov_degrees = math.degrees(fov_radians)
    return fov_degrees


def get_focal_length_for_fov(fov, horizontal_aperture):
    focal_length = horizontal_aperture * 0.5 / math.tan(math.radians(fov * 0.5))
    return focal_length


def get_camera_rotations(camera, start=-90, rotation_span=180):
    """
    Find a list of necessary camera rotations to cover an entire sphere of visibility based on the current camera specs
    Args:
        camera:
        start:
        rotation_span:

    Returns:

    """
    fov = get_camera_fov(camera)
    total_rotation = rotation_span - fov
    camera_rotation_positions = math.ceil(total_rotation / fov)
    start_rotation = start + (fov * .5)
    rotation_increment = total_rotation / camera_rotation_positions

    rotations = []
    angle = start_rotation
    for i in range(0, int(camera_rotation_positions) + 1):
        rotations.append(angle)
        angle += rotation_increment

    return rotations


def layout_uvs_for_nodes(nodes, resolution=4096, umin=0, umax=1, vmin=0, vmax=1):
    """
    Layout all input nodes together in UV space 0 -> 1

    Args:
        nodes (list): List of nodes to layout together
        resolution (int): Resolution of the final texture bake to inform UV shell spacing

    Returns:
        None
    """
    spacing = .0020 * float(4096) / resolution
    offset_u = umin
    offset_v = vmin
    size_u = umax - umin
    size_v = vmax - vmin
    cmds.polyMultiLayoutUV(nodes, layoutMethod=1, scale=1, rotateForBestFit=2, flipReversed=1, percentageSpace=spacing,
                           layout=2, gridU=1, gridV=1, prescale=0, sizeU=size_u, sizeV=size_v, offsetU=offset_u,
                           offsetV=offset_v)


def turn_on_double_sided():
    nodes = cmds.ls(dag=True)
    nodes = [n for n in nodes if cmds.objExists('{}.doubleSided'.format(n))]
    for n in nodes:
        cmds.setAttr("{}.doubleSided".format(n), 1)


def combine_objects(objects, name, parent=None):
    """

    Args:
        objects:
        name:
        parent:

    Returns:

    """
    print 'COMBINING OBJECT', objects
    base_name = name.split("|")[-1]
    node = name
    if len(objects) > 1:
        node = cmds.polyUnite(objects, constructionHistory=False, name=base_name)
    elif len(objects) == 1:
        node = cmds.rename(objects[0], base_name)
    else:
        raise Exception("No objects passed into group -- {}".format(str(objects)))
    try:
        print ' - APPLYING PARENT', parent
        if parent:
            cmds.parent(node, parent)
        elif cmds.listRelatives(node, parent=True):
            cmds.parent(node, world=True)
    except:
        print ' - FAILED TO APPLY PARENT', parent


def combine_children(input_node):
    print 'COMBINE CHILDREN', input_node
    basename = input_node.split("|")[-1]
    temp_parent = input_node + "_TEMP"
    create_group(temp_parent)
    top_parent = (cmds.listRelatives(input_node, parent=True, fullPath=True) or [None])[0]
    children = get_children(input_node)
    for child in children:
        objects = get_mesh_children(child)
        if objects:
            combine_objects(objects, child, parent=temp_parent)
        else:
            continue
    if cmds.objExists(input_node):
        cmds.delete(input_node)
    node = cmds.rename(temp_parent, basename)
    if top_parent and not cmds.objExists(top_parent):
        create_group(top_parent)
    if top_parent:
        cmds.parent(node, top_parent)
    print ' - GENERATED', node


def get_selection_sets():
    return cmds.ls(type="objectSet", l=True)


def group_objects(objects, name, parent=None):
    """

    Args:
        objects:
        name:
        parent:

    Returns:

    """
    objects = cmds.ls(objects)
    if len(objects) >= 1:
        name = cmds.group(objects, name=name)
    else:
        raise Exception("No objects passed into group?")
    if parent:
        # try statement because this fails if the parent is already the parent
        try:
            cmds.parent(name, parent)
        except:
            pass


def get_current_file_name():
    """
    Return current file name
    Returns:
        str: current file name
    """
    path = cmds.file(q=True, sn=True)
    path = path.replace("\\", "/")
    return path


def save_file(output_file):
    dirname = os.path.dirname(output_file)
    if not os.path.exists(dirname):
        os.mkdir(dirname)
    print "Saving '{}'".format(output_file)
    cmds.file(rename=output_file)
    kwargs = {}
    if output_file.endswith(".ma"):
        kwargs["typ"] = "mayaAscii"
    elif output_file.endswith(".mb"):
        kwargs["typ"] = "mayaBinary"
    cmds.file(save=True, options="v=0", **kwargs)


def set_bake_options(node, texture_name, resolution, name):
    """

    Args:
        node:

    Returns:

    """
    output_directory = os.path.dirname(texture_name)
    output_prefix = os.path.basename(texture_name)

    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    options_node = "{}_bake_options".format(name)
    if cmds.objExists(options_node):
        cmds.delete(options_node)
    cmds.createNode("VRayBakeOptions", name=options_node)
    cmds.sets(node, forceElement=options_node, edit=True)

    cmds.setAttr("{}.outputTexturePath".format(options_node), output_directory, type="string")
    cmds.setAttr("{}.filenamePrefix".format(options_node), output_prefix, type="string")
    cmds.setAttr("{}.resolutionX".format(options_node), resolution)

    # Closest
    cmds.setAttr("{}.projMode".format(options_node), 4)


def set_visibility_options(node):
    """
    Args:
        node:

    Returns:


    """
    return
    print 'SET VISIBLITY OPTIONS', node
    options_node = "{}_vray_object_properties".format(node.split("|")[-1])
    if cmds.objExists(options_node):
        cmds.delete(options_node)
    cmds.createNode("VRayObjectProperties", name=options_node)
    cmds.sets(node, forceElement=options_node, edit=True)

    cmds.setAttr("{}.giVisibility".format(options_node), 0)
    cmds.setAttr("{}.primaryVisibility".format(options_node), 0)
    cmds.setAttr("{}.reflectionVisibility".format(options_node), 0)
    cmds.setAttr("{}.refractionVisibility".format(options_node), 0)
    cmds.setAttr("{}.shadowVisibility".format(options_node), 0)
    cmds.setAttr("{}.receiveShadows".format(options_node), 0)


def apply_render_settings(image_format, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult=1):
    """

    Returns:

    """
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "vray", type="string")

    if image_format == "exr":
        image_format = "exr (multichannel)"

    # png, no alpha, rec709
    cmds.setAttr("vraySettings.imgfs", image_format, type="string")
    cmds.setAttr("vraySettings.noAlpha", 0)
    #cmds.setAttr("vraySettings.imgfs", "exr", type="string")

    # Bucket, 1 / 16 / 0.051
    cmds.setAttr("vraySettings.samplerType", 4)
    cmds.setAttr("vraySettings.minShadeRate", min_shading_rate)
    cmds.setAttr("vraySettings.dmcMinSubdivs", 1)
    cmds.setAttr("vraySettings.dmcMaxSubdivs", max_subdivs)
    cmds.setAttr("vraySettings.dmcThreshold", admc_threshold)

    # Lanczos, filter size 2
    cmds.setAttr("vraySettings.aaFilterType", 3)
    cmds.setAttr("vraySettings.aaFilterSize", 2)

    # Subpixel, clamp, clamp level
    cmds.setAttr("vraySettings.cmap_subpixelMapping", 1)
    cmds.setAttr("vraySettings.cmap_clampOutput", 1)
    cmds.setAttr("vraySettings.cmap_clampLevel", 12)

    # GI
    cmds.setAttr("vraySettings.giOn", 1)
    cmds.setAttr("vraySettings.reflectiveCaustics", 0)
    cmds.setAttr("vraySettings.refractiveCaustics", 0)
    cmds.setAttr("vraySettings.primaryEngine", 2)
    cmds.setAttr("vraySettings.secondaryEngine", 0)

    # Increase light samples
    if local_subdivs_mult > 1:
        cmds.setAttr("vraySettings.dmcs_useLocalSubdivs", 1)
        cmds.setAttr("vraySettings.dmcs_subdivsMult", local_subdivs_mult)
    else:
        cmds.setAttr("vraySettings.dmcs_useLocalSubdivs", 0)
    # Full sampling on the lights
    cmds.setAttr("vraySettings.globopt_probabilistic_lights_on", 0)

    # Standard
    cmds.setAttr("vraySettings.globopt_light_doDefaultLights", 0)
    cmds.setAttr("vraySettings.globopt_light_doHiddenLights", 0)
    cmds.setAttr("vraySettings.globopt_geom_doHidden", 0)

    # Bucket size
    cmds.setAttr("vraySettings.sys_regsgen_xc", 32)

    # Set dynamic memory to 0
    cmds.setAttr("vraySettings.sys_rayc_dynMemLimit", 0)


@keep_selection
def bake_object(node, image_format, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult):
    """

    :param node:
    :param image_format:
    :param min_shading_rate:
    :param max_subdivs:
    :param admc_threshold:
    :param local_subdivs_mult:
    :return:

    """
    nodes = get_mesh_children(node)
    if not nodes:
        return

    apply_render_settings(image_format, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult)

    # Options found here: /coppi/global/bin/V-Ray/4.04.03-2018_00000-linux/maya_vray/scripts/vrayBakingMenu.mel
    cmds.optionVar(intValue=("vrayBakeType", 2))
    cmds.optionVar(intValue=("vraySkipNodesWithoutBakeOptions", 1))
    cmds.optionVar(intValue=("vrayAssignBakedTextures", 0))
    cmds.optionVar(intValue=("vrayBakeProjectionBaking", 0))
    cmds.optionVar(stringValue=("vrayBakeOutputPath", ""))

    for node in nodes:
        texture_name = "GARBAGE"
        if os.path.exists(texture_name):
            os.remove(texture_name)
        cmds.select(node, r=True)
        mel.eval("vrayStartBake")


def render(camera):
    pass


def apply_vray_camera_type_to_camera(camera, camera_type=None):
    if cmds.objectType(camera) != "camera":
        camera = (cmds.listRelatives(type="camera", fullPath=True) or [None])[0]
        if not camera:
            raise Exception("No camera found from {}".format(camera))
    mel.eval("vray addAttributesFromGroup {} vray_cameraOverrides 1;".format(camera))
    if camera_type:
        if camera_type == "spherical":
            CAMERA_TYPE = 1
            cmds.setAttr("{}.vrayCameraOverrideFOV".format(camera), 1)
            cmds.setAttr("{}.vrayCameraFOV".format(camera), 360)
        elif camera_type == "cube":
            CAMERA_TYPE = 10
        else:
            raise Exception("Camera type '{}' not recognized".format(camera_type))
        cmds.setAttr("{}.vrayCameraType".format(camera), CAMERA_TYPE)


def apply_vray_stereo_to_camera(camera):
    if cmds.objectType(camera) != "camera":
        camera = (cmds.listRelatives(type="camera", fullPath=True) or [None])[0]
        if not camera:
            raise Exception("No camera found from {}".format(camera))
    mel.eval("vray addAttributesFromGroup {} vray_cameraStereoscopic 1;".format(camera))
    # Top bottom
    cmds.setAttr("{}.vrayCameraStereoscopicOutputLayout".format(camera), 1)


def render_latlong(position, output_image, resolution, min_shading_rate, max_subdivs, admc_threshold,
                   local_subdivs_mult, render_background, image_format, use_default_material, stereo=False,
                   cube_map=False):
    # create camera
    camera = "RENDER_CAMERA"
    camera = create_camera(camera, translation=position)
    set_renderable_camera(camera)
    set_viewport_camera(camera)
    if cube_map:
        # Oculus wants the V-Ray cube map to be reversed and rotated
        device_aspect = 6.0
        apply_vray_camera_type_to_camera(camera, camera_type="cube")
        cmds.setAttr("{}.sx".format(camera), 1)
        cmds.setAttr("{}.ry".format(camera), 180)
    else:
        device_aspect = 2.0
        apply_vray_camera_type_to_camera(camera, camera_type="spherical")

    if stereo:
        device_aspect *= 0.5
        apply_vray_stereo_to_camera(camera)
    apply_render_settings(image_format, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult)
    x = resolution
    y = resolution / device_aspect
    set_render_resolution(x, y)
    if use_default_material:
        use_default_material_for_shading_groups()
    render_frame(output_image, render_background)
    if use_default_material:
        restore_material_for_shading_groups()
    if cmds.objExists(camera):
        cmds.delete(camera)


def qc_render(position, output_image, resolution, fov, min_shading_rate, max_subdivs, admc_threshold,
                   render_background, image_format):
    # create camera
    camera = "QC_CAMERA"
    aperture_inches = 1.0
    aperture_mm = 25.4 * aperture_inches
    focal_length = get_focal_length_for_fov(fov, aperture_mm)
    if not cmds.objExists(camera):
        camera = create_camera(camera, translation=position, focal_length=focal_length, lock_translation=True,
                               horizontal_aperture=aperture_inches, vertical_aperture=aperture_inches)
        set_renderable_camera(camera)
    set_viewport_camera(camera)
    apply_render_settings(image_format, min_shading_rate, max_subdivs, admc_threshold)
    x = resolution
    y = resolution
    set_render_resolution(x, y)
    use_mipmap_material_for_shading_groups()
    render_frame(output_image, render_background)
    restore_material_for_shading_groups()


def delete_empty_child_groups(nodes):
    while 1:
        empty_nodes = set(cmds.ls(nodes, dag=True, long=True, type="transform", leaf=True))
        empty_nodes = list(empty_nodes - set(cmds.ls(nodes, long=True, type="transform", leaf=True)))
        if empty_nodes:
            cmds.delete(empty_nodes)
        else:
            break


def get_nodes_sorted_by_distance(node, viewpoint):
    """

    Args:
        node:

    Returns:

    """
    v3f_viewpoint = imath.V3f(*viewpoint)
    nodes = get_mesh_children(node)

    meshes = cmds.ls(nodes, dag=True, type="mesh", long=True, noIntermediate=True)
    closest_points = [get_closest_point(viewpoint, mesh) for mesh in meshes]
    distances = [(imath.V3f(*p) - v3f_viewpoint).length() for p in closest_points]
    meshes = [o[0] for o in sorted(zip(meshes, distances), key=lambda x:x[1])]
    nodes = [cmds.listRelatives(mesh, parent=True, fullPath=True)[0] for mesh in meshes]

    return nodes


def add_prefix(nodes, prefix):
    for node in nodes:
        new_name = "{}{}".format(prefix, node.split("|")[-1])
        if cmds.objExists(new_name):
            cmds.delete(cmds.ls(new_name))
        cmds.rename(node, new_name)
        print "renaming", node, new_name


def set_render_resolution(x, y, pixel_aspect=1.0):
    cmds.setAttr("vraySettings.width", x)
    cmds.setAttr("vraySettings.height", y)
    cmds.setAttr("vraySettings.pixelAspect", pixel_aspect)


def maya_turn_on_texture_baking(resolution, edge_padding=5):
    """
    Turn on texture baking
    Returns:
        None
    """
    cmds.setAttr("vraySettings.baking_engine", 2)
    cmds.setAttr("vraySettings.giOn", 1)
    cmds.setAttr("vraySettings.globopt_light_doDefaultLights", 0)
    cmds.setAttr("vraySettings.globopt_geom_doHidden", 0)
    cmds.setAttr("vraySettings.bakeAlpha", 0)
    cmds.setAttr("vraySettings.aspectLock", 0)
    cmds.setAttr("vraySettings.pixelAspect", 1)
    set_render_resolution(resolution, resolution)
    cmds.setAttr("vraySettings.noAlpha", 1)
    cmds.setAttr("vraySettings.bakeDilation", edge_padding)


@keep_selection
def set_string_attr_for_selected(attr, value, ad=False):
    selected_nodes = cmds.ls(sl=True, l=True, transforms=True)
    if ad and selected_nodes:
        desends = cmds.listRelatives(selected_nodes, ad=True, f=True, typ='transform')
        if desends:
            selected_nodes.extend(desends)

    for node in selected_nodes:
        if not cmds.objExists("{}.{}".format(node, attr)):
            cmds.addAttr(node, longName=attr, dataType="string")
            cmds.setAttr("{}.{}".format(node, attr), edit=True, keyable=True)
        cmds.setAttr("{}.{}".format(node, attr), value, type="string")


def get_nodes_with_attr_value(attr, value):
    nodes = cmds.ls(l=True, transforms=True)
    nodes = [n for n in nodes if cmds.objExists("{}.{}".format(n, attr))]
    nodes = [n for n in nodes if cmds.getAttr("{}.{}".format(n, attr)) == value]
    return nodes


def select_nodes_with_attr_value(attr, value):
    nodes = get_nodes_with_attr_value(attr, value)
    cmds.select(nodes)


def delete_nodes_attr(attr):
    selected_nodes = cmds.ls(sl=True, l=True, transforms=True)
    for n in selected_nodes:
        # if cmds.attributeQuery(attr, node=n, exists=True):
        if cmds.objExists("{}.{}".format(n, attr)):
            cmds.deleteAttr("{}.{}".format(n, attr))


def get_node_attr_value(node, attr):
    return_value = ""
    node = cmds.ls(node, l=True)[0]
    while node:
        if cmds.objExists("{}.{}".format(node, attr)):
            return_value = cmds.getAttr("{}.{}".format(node, attr))
            break
        node = node.rsplit("|", 1)[0]
    return return_value


def get_attr_value_for_all_nodes(attr):
    nodes = cmds.ls(l=True, transforms=True)
    nodes = [n for n in nodes if cmds.objExists("{}.{}".format(n, attr))]
    return_dict = {}
    for node in nodes:
        return_dict[node] = cmds.getAttr("{}.{}".format(node, attr))
    return return_dict


def maya_set_render_name(texture_name):
    """
    Sets the render file name output for vray in maya

    Args:
        texture_name (str): Full output texture path

    Returns:
        None
    """
    cmds.setAttr("vraySettings.fileNamePrefix", texture_name, type="string")


def maya_turn_off_texture_baking():
    cmds.setAttr("vraySettings.baking_engine", 1)
    cmds.setAttr("vraySettings.dmcs_useLocalSubdivs", 0)


@print_func_name
def create_color_catch_shader():
    material_node = "flat_lambert"
    shading_group = material_node + "SG"
    for node in [material_node, shading_group]:
        if cmds.objExists(node):
            cmds.delete(node)

    cmds.shadingNode("lambert", asShader=True, name=material_node)
    cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shading_group)

    try:
        cmds.connectAttr("{}.outColor".format(material_node), "{}.surfaceShader".format(shading_group), force=True)

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    cmds.setAttr("{}.color".format(material_node), 1, 1, 1, type="double3")

    return shading_group


def assign_color_catch_shader(nodes):
    shading_group = create_color_catch_shader()
    cmds.sets(nodes, e=True, forceElement=shading_group)


@keep_selection
def bake_vertex_colors_for_objects(nodes, color_set="lightbake"):
    maya_turn_on_vertex_baking(color_set)
    assign_color_catch_shader(nodes)
    create_oculus_box_lights()
    delete_vertex_colors(nodes, color_set)
    cmds.select(nodes, r=True)
    mel.eval("vrend")
    maya_turn_off_vertex_baking()


def get_children(node):
    """
    Get the immediate children of a node

    Args:
        node (str): name of the maya node

    Returns:
        list: the immediate children of the input node
    """
    if cmds.objExists(node):
        nodes = cmds.listRelatives(node, children=True, fullPath=True) or []
    else:
        nodes = []
    return nodes


#####################################
# Note that optionVars are global across all maya sessions
def set_option_var(name, **kwdict):
    old_value = get_option_vars(name)
    for k, v in kwdict.iteritems():
        old_value[k] = v
    cmds.optionVar(stringValue=(name, str(old_value)))


def get_option_var(name):
    value = ""
    if cmds.optionVar(exists=name):
        value = cmds.optionVar(q=name)

    if value:
        value = eval(value)
    else:
        value = dict()

    return value


def clear_option_var(name):
    if cmds.optionVar(exists=name):
        cmds.optionVar(remove=name)
#####################################

@keep_selection
def preferences_attr(attr):
    node = "bake_preferences_node"
    if not cmds.objExists(node):
        cmds.createNode("script", name=node)
        cmds.addAttr(node, longName=attr, dataType="string")
        cmds.setAttr("{}.{}".format(node, attr), edit=True, keyable=True)
    return "{}.{}".format(node, attr)


def clear_preferences():
    node = "bake_preferences_node"
    if cmds.objExists(node):
        cmds.delete(node)


def set_preferences(name, **kwdict):
    attr = preferences_attr(name)
    old_value = get_preferences(name)
    for k, v in kwdict.iteritems():
        old_value[k] = v
    cmds.setAttr(attr, str(old_value), type="string")


def get_preferences(name):
    attr = preferences_attr(name)
    value = ""
    if cmds.objExists(attr):
        value = cmds.getAttr(attr)
    if value:
        value = eval(value)
    else:
        value = dict()
    return value


def set_renderable_camera(camera):
    for cam in cmds.ls(cameras=True):
        cmds.setAttr("{}.renderable".format(cam), 0)
    cmds.setAttr("{}.renderable".format(camera), 1)


def set_viewport_camera(camera):
    active_view = get_active_viewport()
    cmds.modelEditor(active_view, camera=camera, edit=True)


def cache_material_for_shading_group(sg):
    attr_name = "vrbake_cache_material"
    attr = "{}.{}".format(sg, attr_name)
    material = (cmds.listConnections("{}.surfaceShader".format(sg)) or [None])[0]
    if material:
        if not cmds.objExists(attr):
            cmds.addAttr(sg, longName=attr_name, dataType="string")
            cmds.setAttr(attr, edit=True, keyable=True)
        cmds.setAttr(attr, material, type="string")


def get_cache_material_for_shading_group(sg):
    attr_name = "vrbake_cache_material"
    attr = "{}.{}".format(sg, attr_name)
    if cmds.objExists(attr):
        return cmds.getAttr(attr)
    else:
        return None


def use_default_material_for_shading_groups():
    material = cmds.listConnections("initialShadingGroup.surfaceShader")[0]
    use_override_material_for_shading_groups(material)


def use_mipmap_material_for_shading_groups():
    shading_group = create_mipmap_debug_material()
    material = cmds.listConnections("{}.surfaceShader".format(shading_group))[0]
    use_override_material_for_shading_groups(material)


@print_func_name
def use_override_material_for_shading_groups(material):
    shading_groups = cmds.ls(type="shadingEngine")
    for sg in shading_groups:
        cache_material_for_shading_group(sg)

        try:
            cmds.connectAttr("{}.outColor".format(material), "{}.surfaceShader".format(sg), force=True)

        except RuntimeError as re:
            # if cmds.attributeExists("output")
            # if cmds.attributeExists("color")
            print "SHADER CONNECTION ERROR: ", re


@print_func_name
def restore_material_for_shading_groups():
    shading_groups = cmds.ls(type="shadingEngine")
    for sg in shading_groups:
        material = get_cache_material_for_shading_group(sg)
        if material and cmds.objExists(material):
            try:
                cmds.connectAttr("{}.outColor".format(material), "{}.surfaceShader".format(sg), force=True)

            except RuntimeError as re:
                # if cmds.attributeExists("output")
                # if cmds.attributeExists("color")
                print "SHADER CONNECTION ERROR: ", re


@print_func_name
def add_ray_switch_to_diffuse_materials():
    """
    Find all materials in the scene that have a diffuse component and connect a switch to allow deactivating the
    diffuse for all primary rays.
    """
    node_suffix = "__multiply_vrbake"
    sampler_info = create_sampler_info()
    condition = create_condition("ray_depth_greater_than_zero")
    try:
        a, b = "{}.vrayRayDepth".format(sampler_info), "{}.firstTerm".format(condition)
        if not cmds.isConnected(a, b):
            cmds.connectAttr(a, b, force=True)

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    GREATER_THAN = 2
    cmds.setAttr("{}.operation".format(condition), GREATER_THAN)
    cmds.setAttr("{}.colorIfTrue".format(condition), 1, 1, 1)
    cmds.setAttr("{}.colorIfFalse".format(condition), 0, 0, 0)

    materials = [m for m in cmds.ls(materials=True) if cmds.objExists("{}.color".format(m))]
    for material in materials:
        # Setup multiplication node
        multiply_name = "{}{}".format(material, node_suffix)
        # Create input 2 node name as 'condiion'
        multiply_condition_input_plug = "{}.input2".format(multiply_name)
        # Create input 1 node nmae as 'diffuse'
        multiply_diffuse_input_plug = "{}.input1".format(multiply_name)
        # Create the node
        create_multiply(multiply_name)

        material_diffuse_plug = "{}.color".format(material)
        diffuse_plug = (cmds.listConnections(material_diffuse_plug, destination=False, source=True, plugs=True) or [None])[0]
        multiply_output_plug = "{}.output".format(multiply_name)

        if diffuse_plug and diffuse_plug.split(".")[0].endswith(node_suffix):
            continue

        try:
            a, b = "{}.outColor".format(condition), multiply_condition_input_plug
            if not cmds.isConnected(a, b):
                cmds.connectAttr(a, b, force=True)

        except RuntimeError as re:
            # if cmds.attributeExists("output")
            # if cmds.attributeExists("color")
            print "SHADER CONNECTION ERROR: ", re

        if diffuse_plug:
            cmds.disconnectAttr(diffuse_plug, material_diffuse_plug)
            cmds.connectAttr(diffuse_plug, multiply_diffuse_input_plug)
        else:
            diffuse_value = cmds.getAttr(material_diffuse_plug)[0]
            cmds.setAttr(multiply_diffuse_input_plug, *diffuse_value)

        try:
            a, b = multiply_output_plug, material_diffuse_plug
            if not cmds.isConnected(a, b):
                cmds.connectAttr(a, b, force=True)

        except RuntimeError as re:
            # if cmds.attributeExists("output")
            # if cmds.attributeExists("color")
            print "SHADER CONNECTION ERROR: ", re


@print_func_name
def remove_ray_switch_from_diffuse_materials():
    node_suffix = "__multiply_vrbake"
    materials = [m for m in cmds.ls(materials=True) if cmds.objExists("{}.color".format(m))]
    for material in materials:
        material_diffuse_plug = "{}.color".format(material)
        multiply_node = (cmds.listConnections(material_diffuse_plug, destination=False, source=True, plugs=False) or [None])[0]
        multiply_diffuse_input_plug = "{}.input1".format(multiply_node)
        multiply_output_plug = "{}.output".format(multiply_node)
        if not cmds.nodeType(multiply_node) == "multiplyDivide" or not multiply_node.endswith(node_suffix):
            continue
        diffuse_plug = (cmds.listConnections(multiply_diffuse_input_plug, destination=False, source=True, plugs=True) or [
            None])[0]
        cmds.disconnectAttr(multiply_output_plug, material_diffuse_plug)
        if diffuse_plug:
            try:
                a, b = diffuse_plug, material_diffuse_plug
                if not cmds.isConnected(a, b):
                    cmds.connectAttr(a, b, force=True)
            except RuntimeError as re:
                # if cmds.attributeExists("output")
                # if cmds.attributeExists("color")
                print "SHADER CONNECTION ERROR: ", re
        else:
            diffuse_value = cmds.getAttr(multiply_diffuse_input_plug)[0]
            cmds.setAttr(material_diffuse_plug, *diffuse_value)
        cmds.delete(multiply_node)


def setup_render_mode(mode, camera):
    delete_render_elements()

    create_render_element("lighting")
    create_render_element("gi")
    create_render_element("selfIllum")
    create_render_element("specular")
    create_render_element("reflect")
    create_render_element("refract")
    create_render_element("normals")
    create_facing_ratio_render_element()

    if mode == "reflection":
        add_ray_switch_to_diffuse_materials()
        cmds.setAttr("vraySettings.bakeFromCamera", 1)
        set_renderable_camera(camera)
        set_viewport_camera(camera)
        cmds.setAttr("vraySettings.globopt_mtl_reflectionRefraction", 1)
        cmds.setAttr("vraySettings.globopt_mtl_glossy", 1)
    else:
        cmds.setAttr("vraySettings.bakeFromCamera", 0)
        cmds.setAttr("vraySettings.globopt_mtl_reflectionRefraction", 0)
        cmds.setAttr("vraySettings.globopt_mtl_glossy", 0)


def create_multiply(name=None):
    if name == None:
        name = "multiply"
    if not cmds.objExists(name):
        node = cmds.shadingNode("multiplyDivide", asUtility=True)
        cmds.rename(node, name)
    return name


def create_condition(name=None):
    if name == None:
        name = "condition"
    if not cmds.objExists(name):
        node = cmds.shadingNode("condition", asUtility=True)
        cmds.rename(node, name)
    return name


def create_sampler_info():
    sampler_info_node = "samplerInfo1"
    if not cmds.objExists(sampler_info_node):
        node = cmds.shadingNode("samplerInfo", asUtility=True)
        cmds.rename(node, sampler_info_node)
        mel.eval("vray addAttributesFromGroup {} vray_samplerinfo_extra_tex 1;".format(sampler_info_node))
    return sampler_info_node


@print_func_name
def create_facing_ratio_render_element():
    sampler_info_node = create_sampler_info()
    facing_ratio_extra_tex = "vrayRE_Extra_Tex_facingRatio"
    if not cmds.objExists(facing_ratio_extra_tex):
        node = create_render_element("ExtraTex")
        cmds.rename(node, facing_ratio_extra_tex)
    try:
        cmds.connectAttr("{}.facingRatio".format(sampler_info_node), "{}.vray_texture_extratexR".format(facing_ratio_extra_tex), force=True)
        cmds.connectAttr("{}.flippedNormal".format(sampler_info_node), "{}.vray_texture_extratexG".format(facing_ratio_extra_tex), force=True)
        cmds.setAttr("{}.vray_name_extratex".format(facing_ratio_extra_tex), "facingRatio", type="string")
        cmds.setAttr("{}.enableDeepOutput".format(facing_ratio_extra_tex), 0)

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re


def get_render_element_full_name(name):
    suffix = "Channel"
    if name in ["ExtraTex", "MultiMatte"]:
        suffix = "Element"
    type_full_name = "{}{}".format(name, suffix)
    return type_full_name


def create_render_element(name):
    node = get_render_element(name)
    if name in ["ExtraTex", "MultiMatte"] or not node:
        type_full_name = get_render_element_full_name(name)
        node = mel.eval("vrayAddRenderElement {}".format(type_full_name))
    return node


def delete_render_elements():
    nodes = cmds.ls(type="VRayRenderElement")
    if nodes:
        cmds.delete(nodes)


def get_render_element(name):
    render_elements = cmds.ls(type="VRayRenderElement")
    type_full_name = get_render_element_full_name(name)
    for node in render_elements:
        elem_type = cmds.getAttr("{}.vrayClassType".format(node))
        if elem_type == type_full_name:
            return node
    return None


def export_vrscene_file(output_vrscene):
    cmds.setAttr("vraySettings.vrscene_on", 1)
    cmds.setAttr("vraySettings.vrscene_render_on", 0)
    cmds.setAttr("vraySettings.vrscene_filename", output_vrscene, type="string")
    cmds.setAttr("vraySettings.misc_separateFiles", 0)
    cmds.setAttr("vraySettings.misc_eachFrameInFile", 0)
    cmds.setAttr("vraySettings.misc_stripPaths", 0)
    cmds.setAttr("vraySettings.misc_meshAsHex", 1)
    cmds.setAttr("vraySettings.misc_transformAsHex", 1)
    cmds.setAttr("vraySettings.misc_compressedVrscene", 1)
    cmds.setAttr("vraySettings.animType", 0)

    mel.eval("vrayShowVFB()")
    mel.eval("vrayResetVFB()")
    mel.eval("RenderIntoNewWindow;")

    # Turn off before exit
    cmds.setAttr("vraySettings.vrscene_render_on", 1)
    cmds.setAttr("vraySettings.vrscene_on", 0)


def render_in_background():
    output_file = cmds.getAttr("vraySettings.fileNamePrefix")
    output_vrscene = output_file + ".vrscene"
    export_vrscene_file(output_vrscene)
    if not os.path.exists(output_vrscene):
        raise Exception("Did not create {} ...".format(output_vrscene))

    vray_exe = os.path.join(
        os.getenv("VRAY_PATH"),
        "vray.exe"
    )
    maya_env = os.environ.copy()
    for k, v in maya_env.iteritems():
        # Make sure we don't have unicode, which causes subprocess to choke
        maya_env[k] = str(v)

    distributed_on = cmds.getAttr("vraySettings.sys_distributed_rendering_on")

    cmd = [
        vray_exe,
        "-sceneFile={}".format(output_vrscene),
        "-display=0",
    ]
    if distributed_on:
        import vray.vray_dr_manager as v
        local_on = cmds.getAttr("vraySettings.sys_distributed_rendering_local")
        servers = [host.host for host in v.VRayDRManager.instance().servers]
        if local_on:
            cmd.append("-distributed=1")
        else:
            cmd.append("-distributed=2")
        if servers:
            cmd.append('-renderhost="{}"'.format(";".join(servers)))
    subprocess.call(cmd, env=maya_env)
    os.remove(output_vrscene)


def render_frame(output_file, render_background=False):
    print "Rendering '{}' ...".format(output_file)
    nodes = cmds.ls(sl=True)
    [file_base, ext] = os.path.splitext(output_file)
    maya_set_render_name(file_base)
    if render_background:
        render_in_background()
        remove_ray_switch_from_diffuse_materials()

    else:
        cmds.setAttr("vraySettings.vrscene_on", 0)
        mel.eval("vrayResetVFB()")
        mel.eval("vrayShowVFB()")
        mel.eval("RenderIntoNewWindow;")

    if not os.path.exists(output_file):
        temp_file = (file_base + "_tmp" + ext)
        if os.path.exists(temp_file):
            os.rename(temp_file, output_file)
        else:
            raise Exception("Cannot find files {} or {}".format(output_file, temp_file))


def _oiio_convert(src, dest, colspace='sRGB'):

    import psylaunch

    _args = [
        src,
        '-ch',
        'R,G,B',
        '--tocolorspace',
        colspace,
        '-o',
        dest]

    if os.path.exists(dest):
        os.remove(dest)
    assert os.path.exists(src)
    _pipe = psylaunch.launch_app('oiiotool', args=_args, communicate=True)
    print _pipe.stdout.read()
    print _pipe.stderr.read()
    print 'CMD', 'launch oiiotool --', ' '.join(_args)
    assert os.path.exists(dest)


@keep_selection
def bake_textures(
        name, input_nodes, resolution, default_file=None, spec_file=None):
    """
    Bake textures for the given node list, using the first node for the name.

    Args:
        input_nodes (list): Input list of nodes to bake into a single output
        texture_name (str): Full path to the output texture
        resolution (int): Texture bake resolution in pixels

    Returns:
        (str list): list of successfully exported files
    """
    dprint('BAKE TEXTURES', name, input_nodes)
    print' - EXPORT PATH', default_file

    _enable_aovs = False
    _outputs = []
    _tmp_dir = abs_path('{}/arnold_bake'.format(tempfile.gettempdir()))

    # Build tmp node
    _temp_node = name + "_TEMP"
    print ' - TEMP NODE', _temp_node
    if cmds.objExists(_temp_node):
        cmds.delete(_temp_node)
    _temp_bake_objects = cmds.duplicate(input_nodes)
    print ' - INPUT NODES', input_nodes
    combine_objects(_temp_bake_objects, _temp_node)
    _shp = get_shp(_temp_node)
    # [cmds.setAttr("{}.visibility".format(node), 0) for node in input_nodes]
    set_visibility_options(_temp_node)
    cmds.select(_temp_node)
    print ' - SEL', cmds.ls(selection=True)

    # Prepare outputs
    _tmp_base = str(_shp).replace('|', '_')
    if default_file:
        _out_file = File(default_file)
        _tmp_file = File(abs_path('{}/{}.exr'.format(
            _tmp_dir, _tmp_base)))
        _outputs.append((_tmp_file, _out_file))
    if spec_file:
        if not cmds.objExists('aiAOV_specular'):
            mtoa.aovs.AOVInterface().addAOV('specular')
        _enable_aovs = True
        _out_file = File(spec_file)
        _tmp_file = File(abs_path('{}/{}.specular.exr'.format(
            _tmp_dir, _tmp_base)))
        _outputs.append((_tmp_file, _out_file))
    for _, _out_file in _outputs:  # Clear output paths
        if _out_file.exists():
            _out_file.delete(force=True)
    if os.path.exists(_tmp_dir):
        shutil.rmtree(_tmp_dir)
    test_path(_tmp_dir)

    # Generate bakes to tmp dir
    _start = time.time()
    cmds.arnoldRenderToTexture(
        folder=_tmp_dir, resolution=resolution, enable_aovs=_enable_aovs)
    _dur = time.time() - _start
    print' - GENERATED BAKE IN {:.02f}s'.format(time.time() - _start)

    # Move to output dir + convert to required extension
    for _tmp_file, _out_file in _outputs:
        print ' - MOVING', _tmp_file.path
        print ' - TARGET', _out_file.path
        assert _tmp_file.exists()
        if _out_file.extn == _tmp_file.extn:
            shutil.move(_tmp_file.path, _out_file.path)
        else: # Convert + duplicate exr
            _oiio_convert(_tmp_file.path, _out_file.path)
            shutil.move(_tmp_file.path, _out_file.apply_extn('exr').path)

    return [_out_file.path for _, _out_file in _outputs]


@keep_selection
def export_fbx(node, output_name):
    cmds.select(node)
    load_plugin('fbxmaya')
    cmds.file(output_name, options="v=0;", typ="FBX export", pr=True, es=True, force=True)


def duplicate_node(node, new_name, parent=None, upstream_nodes=False, force=True, visible=None):
    """
    Duplicate a given node and its children, then optionally parent it

    Args:
        node (str): Name of the node to duplicate
        new_name (str): Name for the new duplicate
        parent (str): Name of a node to use for the parent of the new duplicate
        upstream_nodes (bool): Optionally copy all upstream nodes.  Default is False
        force (bool): Force will delete an existing node with the same name
        visible (bool): visible wlil force a duplicate to be either visible or hidden depending on this flag

    Returns:
        str: New duplicate name
    """
    if not cmds.objExists(node):
        return ""

    if force and cmds.objExists(new_name):
        cmds.delete(new_name)
    if upstream_nodes:
        kwargs = { "upstreamNodes" : upstream_nodes }
    else:
        kwargs = {}

    node = cmds.duplicate(node, returnRootsOnly=True, **kwargs)[0]
    cmds.rename(node, new_name)
    if parent != None:
        cmds.parent(new_name, parent)
    if visible:
        cmds.setAttr("{}.visibility".format(new_name), visible)
    return new_name


def delete_hidden_children(top_node):
    """
    Delete all child nodes that are hidden

    Args:
        top_node (str): Name of the top node within maya

    Returns:
        None
    """
    nodes = cmds.ls(top_node, dag=True, long=True)
    nodes = [node for node in nodes if not cmds.getAttr("{}.visibility".format(node))]
    if nodes:
        cmds.delete(nodes)


def delete_children_with_string_match(top_node, input_string):
    """
    Delete all child nodes that contain string match

    Args:
        top_node (str): Name of the top node within maya
        input_string (str): Regex wildcard string match

    Returns:
        None
    """
    nodes = cmds.ls(top_node, dag=True, long=True)
    nodes = [node for node in nodes if re.search(input_string, node)]
    if nodes:
        cmds.delete(nodes)


def delete_vertex_colors(nodes, color_set=None):
    """
    Delete vertex colors for input nodes
    Args:
        nodes (list): Nodes to process
        color_set (str): Name of the color set to delete.  If None, this deletes all vertex colors.

    Returns:
        None
    """
    try:
        nodes = get_mesh_children(nodes)
        for node in nodes:
            all_color_sets = cmds.polyColorSet(node, q=True, allColorSets=True) or []
            for each_color_set in all_color_sets:
                if color_set == None or color_set == each_color_set:
                    cmds.polyColorSet(node, colorSet=each_color_set, delete=True)
    except:
        import traceback
        traceback.print_exc()


def disable_screen_space_ambient_occlusion():
    cmds.setAttr("hardwareRenderingGlobals.ssaoEnable", 0)


def get_vertex_colors_for_object(node):
    """
    Return all vertex color sets for an object

    Args:
        node (str): Maya input object

    Returns:
        list: list of vertex color names
    """
    return cmds.polyColorPerVertex("{}.vtx[*]".format(node), q=True, r=True)


def full_screen_on():
    """
    Activate full screen view in the main maya window
    Returns:
        None
    """
    mel.eval("dR_updateToolSettings;")
    mel.eval("ToggleFullScreenMode;")
    mel.eval("toggleMainWindowFullScreenMode;")
    mel.eval("toggleMainWindowFullScreenModeDefer 0 MainPane;")


def full_screen_off():
    """
    Deactivate full screen mode in the main maya window
    Returns:
        None
    """
    mel.eval("ToggleFullScreenMode;")
    mel.eval("toggleMainWindowFullScreenMode;")
    mel.eval("toggleMainWindowFullScreenModeDefer 1 MainPane;")
    mel.eval("workingMode modelingMenuSet;")


@keep_selection_mode
@keep_selection
def get_face_count_in_camera_frustum(camera):
    """
    Get a list of faces visible from the maya viewport

    Returns:
        list: list of faces from the screen
    """
    all_nodes = cmds.ls(assemblies=True)
    cmds.select(all_nodes)

    active_view = get_active_viewport()
    viewport_width = cmds.control(active_view, q=True, w=True)
    viewport_height = cmds.control(active_view, q=True, h=True)

    # Depth selection makes it so only the first face is counted
    cmds.selectPref(useDepth=True)
    cmds.selectPref(autoUseDepth=True)

    cmds.selectMode(component=True)
    cmds.selectType(allComponents=False)
    cmds.selectType(polymeshFace=True)

    active_view = get_active_viewport()
    # Needed to make sure they aren't in wireframe
    cmds.modelEditor(active_view, displayAppearance="wireframe", edit=True)

    cmds.refresh()
    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    om.MGlobal.selectFromScreen(0, 0, viewport_width, viewport_height, om.MGlobal.kSurfaceSelectMethod)

    nodes = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(nodes)

    # Restore selection
    om.MGlobal.setActiveSelectionList(sel, om.MGlobal.kReplaceList)

    # Return the nodes as strings
    from_screen = []
    nodes.getSelectionStrings(from_screen)

    faces = cmds.ls(from_screen, flatten=True)
    return len(faces)


def get_faces_from_screen():
    """
    Get a list of faces visible from the maya viewport

    Returns:
        list: list of faces from the screen
    """

    active_view = get_active_viewport()
    viewport_width = cmds.control(active_view, q=True, w=True)
    viewport_height = cmds.control(active_view, q=True, h=True)

    # Depth selection makes it so only the first face is counted
    cmds.selectPref(useDepth=True)
    cmds.selectPref(autoUseDepth=True)

    cmds.selectMode(component=True)
    cmds.selectType(allComponents=False)
    cmds.selectType(polymeshFace=True)

    active_view = get_active_viewport()

    # Needed to make sure they aren't in wireframe
    cmds.modelEditor(active_view, displayAppearance="smoothShaded", edit=True)
    cmds.modelEditor(active_view, displayAppearance="flatShaded", edit=True, i=False, ocl=True)

    # Turn off textures for speed
    cmds.modelEditor(active_view, displayTextures=False, edit=True)

    # Update the scene
    cmds.refresh()

    # Setup an API selection list to hold our current selection
    sel = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(sel)

    # Setup a selection mask to get the face components
    om.MGlobal.setSelectionMode (om.MGlobal.kSelectComponentMode)
    comMask = om.MSelectionMask (om.MSelectionMask.kSelectMeshFaces)
    om.MGlobal.setComponentSelectionMask(comMask)

    # Do the actual selection
    om.MGlobal.selectFromScreen(0, 0, viewport_width, viewport_height, om.MGlobal.kReplaceList, om.MGlobal.kSurfaceSelectMethod)

    # Setup an API selection node to hold our currently selected faces
    nodes = om.MSelectionList()
    om.MGlobal.getActiveSelectionList(nodes)

    # Restore selection
    om.MGlobal.setActiveSelectionList(sel, om.MGlobal.kReplaceList)

    # Store the selected nodes as strings
    from_screen = []
    nodes.getSelectionStrings(from_screen)

    # Get the selectable long names of the selected faces
    faces = cmds.ls(from_screen, long=True)

    return [] if faces is None else faces


def get_camera_coverage_rotations(name):
    """
    Get the rotations required to cover a complete projection volume with the given camera and FOV
    Args:
        name:

    Returns:
        list: List of camera rotations, [[x, y, z], [x, y, z], ...]
    """
    x_camera_rotations = get_camera_rotations(name, start=-90, rotation_span=180)
    y_camera_rotations = get_camera_rotations(name, start=0, rotation_span=360)

    camera_rotations = []
    for y in y_camera_rotations:
        for x in x_camera_rotations:
            camera_rotations.append([x, y, 0])

    return camera_rotations


def get_faces_visible_from_point(nodes, point, near_clip, far_clip, single_cam_focal_length=18):
    """
    Checks in a sphere around the given point to see which faces from the objects in the list are visible.
    Args:
        nodes:
        point:

    Returns:
        list: faces visible from the given point
    """
    tx = point[0]
    ty = point[1]
    tz = point[2]
    camera = create_camera(
        "selection_cam",
        focal_length=single_cam_focal_length,
        horizontal_aperture=1, vertical_aperture=1,
        film_fit="vertical",
        far_clip=far_clip, near_clip=near_clip
    )

    camera_rotations = get_camera_coverage_rotations(camera)

    set_viewport_camera(camera)
    cmds.select(nodes)
    cmds.xform(camera, t=[tx, ty, tz], a=True)

    face_list = []
    for [rx, ry, rz] in camera_rotations:
        # Loop through camera rotations
        cmds.xform(camera, rotation=[rx, ry, rz], a=True)

        # Do the actual face selection
        faces_from_screen = get_faces_from_screen()

        if faces_from_screen:
            face_list.extend(faces_from_screen)

        # If we want to use a camera in each rotation to build the frustrum widget
        # it could be done here
        pass

    cmds.delete(camera)

    return face_list


def get_points_for_hemisphere(center, radius, horizontal_steps=4, vertical_steps=3):
    # type: (list, float, int, int) -> list
    """
    Find points defining the outside of a hemisphere with a given radius.
        Center and Radius are coming from preset JSON files
        Horizontal and Vertical Steps come from Geometry Occlusion Options panel in th UI

    Args:
        :param center: (list) [x, y, z] defining the center of the hemisphere
        :param radius: Radius is scene units (?)
        :param horizontal_steps:  Number of steps horizontally around the hemisphere
        :param vertical_steps: Number of steps vertically
        :return: list of imath.V3f points for the points around the hemisphere
    """
    center = imath.V3f(*center)
    horizontal_increment = math.radians(360.0 / horizontal_steps)
    vertical_increment = math.radians(90.0 / vertical_steps)
    point_list = []
    for x_index in range(0, vertical_steps):
        for y_index in range(0, horizontal_steps):
            x_rotation = x_index * vertical_increment
            y_rotation = y_index * horizontal_increment
            y = round(math.sin(x_rotation) * radius, 5)
            xy_length = math.cos(x_rotation) * radius
            x = round(math.sin(y_rotation) * xy_length, 5)
            z = round(math.cos(y_rotation) * xy_length, 5)
            point = imath.V3f(x, y, z) + center

            if point not in point_list:
                point_list.append(point)

    # Add one point on top and center point
    point_list.append(imath.V3f(0, radius, 0) + center)
    point_list.append(center)
    return point_list


def draw_camera_frustrum():
    """Builds frustum geometry based on the selected camera."""
    # --------- Gather relevant camera attributes
    camera = cmds.ls(selection=True)

    if not cmds.objectType(camera, isType="camera"):
        print "ERROR: You need to select a camera."
        sys.exit(0)

    focalLength = cmds.getAttr("{}.focalLength".format(camera[0]))
    horizontalAperture = cmds.getAttr("{}.cameraAperture".format(camera[0]))[0][0]
    verticalAperture = cmds.getAttr("{}.cameraAperture".format(camera[0]))[0][1]
    nearClipping = cmds.getAttr("{}.nearClipPlane".format(camera[0]))
    farClipping = cmds.getAttr("{}.farClipPlane".format(camera[0]))

    print "---- Camera Attributes:\n\tfocal length: {}\n\thorizontal aperture: {}".format(focalLength, horizontalAperture)

    # --------- compute FOV just for kicks, and to verify numbers match
    adjacent = focalLength
    opposite = horizontalAperture * .5 * 25.4

    print "---- Right Triangle Values:\n\tadjacent: {}\n\topposite: {}".format(adjacent, opposite)

    horizontalFOV = math.degrees(math.atan(opposite / adjacent)) * 2

    print "\tcomputed horizontal FOV: {}".format(horizontalFOV)

    # --------- calculate ratios
    plane = horizontalAperture * 25.4
    nearScaleValue = nearClipping * plane / focalLength
    farScaleValue = farClipping * plane / focalLength

    print "---- Lens:\n\tprojection ratio: {}".format(plane / focalLength)

    # --------- build geometry
    myCube = cmds.polyCube(w=1, h=1, d=farClipping - nearClipping, sy=1, sx=1, sz=1, ax=[0, 1, 0], ch=1,
                           name=camera[0].replace("Shape", "Frustrum"))

    cmds.setAttr(myCube[0] + ".translateZ", nearClipping + (farClipping - nearClipping) * .5)
    cmds.makeIdentity(apply=True, t=1, r=1, s=1, n=0, pn=1);
    cmds.setAttr(myCube[0] + ".rotatePivotZ", 0)
    cmds.setAttr(myCube[0] + ".scalePivotZ", 0)
    cmds.setAttr(myCube[0] + ".rotateY", 180)

    # --------- use expressions to update frustum geo as FOV and apertures are changed
    scaleX = "{}.scaleZ*{}.farClipPlane*{}.horizontalFilmAperture*25.4/{}.focalLength".format(myCube[0], camera[0],
                                                                                              camera[0], camera[0])
    scaleY = "{}.scaleZ*{}.farClipPlane*{}.verticalFilmAperture*25.4/{}.focalLength".format(myCube[0], camera[0],
                                                                                            camera[0], camera[0])

    cmds.move(0, 0, 0, myCube[0] + ".f[2]", absolute=True)
    cmds.scale(nearScaleValue, 0, 1, myCube[0] + ".f[2]", pivot=[0, 0, 0])
    cmds.expression(
        s="{}.scaleX = {};{}.scaleY = {};".format(myCube[0], scaleX, myCube[0], scaleY),
        n="{}_Expr".format(myCube[0]))
    cmds.parent(myCube, camera, relative=True)


@keep_selection
@fullscreen_on
@keep_selection_mode
@print_func_name
def delete_occluded_faces(nodes, view_points, near_clip, far_clip):
    # type: (list, list, float, float) -> None
    """
    March through multiple camera positions to find and delete all occluded faces.  Also deletes all "invisible"
    nodes, meaning the nodes where no faces are visible from camera.

        :param nodes:
        :param view_points:
        :param near_clip:
        :param far_clip:
        :rtype: None
    """
    isolate_in_viewport(nodes)
    all_visible_faces = []
    # faces_dict = {}

    # Loop though view point locations
    for point in qt.progress_bar(
            view_points, 'Processing {:d} view{}', col='MediumAquamarine'):  # [0:1]:
        # Collect all the face(ids?) of visible faces for the given nodes
        point_visible_faces = get_faces_visible_from_point(nodes, point, near_clip, far_clip, single_cam_focal_length=18)

        if point_visible_faces:
            # Add the list of faces to the collective list
            all_visible_faces.extend(point_visible_faces)
            # faces_dict.update({"visible_{}".format(pprint.pformat(point)): point_visible_faces})

    # if True:
    current_nodes = get_mesh_children(nodes)
    # Get the full paths of the faces
    all_visible_faces = cmds.ls(all_visible_faces, long=True)

    # Use the face list to get a list of visible nodes
    visible_nodes = set([face.split(".")[0] for face in all_visible_faces])

    # Delete any invisible nodes
    invisible_nodes = list(set(current_nodes) - visible_nodes)
    cmds.delete(invisible_nodes)
    # ########################################################################

    current_nodes = get_mesh_children(nodes)
    all_visible_faces = cmds.ls(all_visible_faces, long=True)

    # Select all the child nodes
    faces = ["{}.f[*]".format(node) for node in current_nodes]
    cmds.select(faces, r=True)

    # Deselect visible faces
    cmds.select(all_visible_faces, deselect=True)

    # -----------------------------------------------------------------------------------------[ Delete occluded faces ]
    occluded_faces = cmds.ls(sl=True, l=True)

    cmds.delete(occluded_faces)
    # ########################################################################
    # write_faces_to_file(faces_dict)


def write_faces_to_file(faces):
    import json
    fp = os.path.join(os.environ.get('TEMP'), "faces_list.json")
    with open(fp, 'w') as f:
        json.dump(faces, f)


def get_active_viewport():
    current_model_panel = None
    for model_panel in cmds.getPanel(type="modelPanel"):
        if cmds.modelEditor(model_panel, q=1, av=1):
            current_model_panel = model_panel
            break
    return current_model_panel


def get_active_camera():
    active_viewport = get_active_viewport()
    active_camera = cmds.modelPanel(active_viewport, q=True, camera=True)
    return active_camera


@keep_selection
def isolate_in_viewport(node):
    """

    Args:
        node:

    Returns:

    """
    viewport = get_active_viewport()
    cmds.select(node)

    if not cmds.isolateSelect(viewport, q=True, state=True):
        cmds.isolateSelect(viewport, state=True)
    nodes = cmds.isolateSelect(viewport, q=True, viewObjects=True)
    if nodes:
        cmds.select(nodes)
    cmds.isolateSelect(viewport, removeSelected=True)
    cmds.select(node)

    cmds.isolateSelect(viewport, addSelected=True)


def delete_extra_uv_sets(node):
    """
    Deletes all UV sets for node
    Args:
        node:

    Returns:

    """
    nodes = cmds.ls(node, dag=True, type="mesh", long=True)
    uvset_default = "map1"
    for o in nodes:
        uvsets = cmds.polyUVSet(o, q=True, allUVSets=True)
        if len(uvsets) > 1:
            for uvset in uvsets[1:]:
                try:
                    cmds.polyUVSet(o, delete=True, uvSet=uvset)
                except:
                    print "Cannot delete UV set on '{}'".format(o)
        if uvsets[0] != uvset_default:
            cmds.polyUVSet(o, rename=True, uvSet=uvsets[0], newUVSet=uvset_default)


def delete_nodes(nodes):
    """
    Delete the given nodes
    Args:
        nodes (list): list of maya nodes for deletion

    Returns:
        None
    """
    for node in nodes:
        if cmds.objExists(node):
            cmds.delete(node)


def delete_children(node):
    """
    Delete the given nodes
    Args:
        nodes (list): list of maya nodes for deletion

    Returns:
        None
    """
    for child in get_children(node):
        if cmds.objExists(child):
            cmds.delete(child)


def get_nodes_by_name(name):
    nodes = cmds.ls(name, l=True)
    return nodes


def get_vertex_count_for_node(node):
    """
    Get the vertex count for a given node
    Args:
        node (str): Name of the maya node

    Returns:
        int: vertex count for the node
    """
    return cmds.polyEvaluate(node, v=True)


def get_face_count_for_node(node):
    """
    Get the face count for a given node
    Args:
        node (str): Name of the maya node

    Returns:
        int: face count for the node
    """
    return cmds.polyEvaluate(node, f=True)


@print_func_name
def get_closest_point(point, mesh):
    """
    Given an input point list, get the closest points on a mesh
    Args:
        point (list): points, e.g. [0,0,0]
        mesh (str): Name of the maya input mesh

    Returns:
        list: original points mapped onto the closest points to the given shape
    """
    closest_point_node = cmds.createNode("closestPointOnMesh")
    try:
        cmds.connectAttr("{}.outMesh".format(mesh), "{}.inMesh".format(closest_point_node))
        cmds.connectAttr("{}.worldMatrix[0]".format(mesh), "{}.inputMatrix".format(closest_point_node))

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    cmds.setAttr("{}.inPosition".format(closest_point_node), point[0], point[1], point[2],
                 type="double3")
    position = cmds.getAttr("{}.position".format(closest_point_node))

    cmds.delete(closest_point_node)
    return position


def create_poly_from_points(vertex_positions, name, shading_group="initialShadingGroup"):
    """
    Create a polygon from a list of points.

    Args:
        vertex_positions (list): List of points for the vertex positions, e.g.: [[0,0,0], [0,1,0], [1,0,0], ...]
        name (str): Name of the output mesh

    Returns:
        str: name of the output mesh
    """
    meshFn = om.MFnMesh()

    vertices = [om.MPoint(p[0], p[1], p[2]) for p in vertex_positions]
    # Need to make it evenly divisible by three.  Duplicate the last point until it is.
    for i in range(0, len(vertices).format(3)):
        vertices.append(om.MPoint(vertex_positions[-1][0], vertex_positions[-1][1], vertex_positions[-1][2]))
    poly_faces = [3] * (len(vertices) / 3)

    polygon_connections = []
    for i in range(0, len(poly_faces)):
        j = i * 3
        polygon_connections.append(j)
        polygon_connections.append(j+1)
        polygon_connections.append(j+2)

    # create the mesh
    m_object = meshFn.create(vertices, poly_faces, polygon_connections)
    node = om.MFnDependencyNode(m_object).name()
    node = cmds.rename(node, name)
    if cmds.objExists(shading_group):
        cmds.sets(node, e=True, forceElement=shading_group)
    return node


@keep_selection
@print_func_name
def shrink_wrap_to_mesh(input_mesh, target_mesh):
    """
    Apply shrink wrap deformer to mesh

    Args:
        input_mesh (str): Input mesh that should be deformed
        target_mesh (str): Target mesh to which the input_mesh should move

    Returns:
        str: deformer name
    """
    deformer = cmds.deformer(target_mesh, type="shrinkWrap", ignoreSelected=True)[0]
    cmds.deformer(deformer, e=True, g=target_mesh)
    try:
        cmds.connectAttr("{}.worldMesh[0]".format(input_mesh), "{}.targetGeom".format(deformer))

    except RuntimeError as re:
        # if cmds.attributeExists("output")
        # if cmds.attributeExists("color")
        print "SHADER CONNECTION ERROR: ", re

    return deformer


def get_maya_scene_scale():
    return cmds.currentUnit(q=True, linear=True, fullName=True)


def get_top_parent(node):
    return cmds.ls(node, long=True)[0].split("|")[1]


def node_exists(node):
    if cmds.objExists(node):
        return True
    else:
        return False


def get_current_project():
    path = cmds.workspace(q=True, rd=True)
    path = path.replace("\\", "/")
    return path


def get_file_texture_dict():
    file_texture_dict = {}
    files = cmds.ls(type="file")
    for f in files:
        texture = cmds.getAttr("{}.fileTextureName".format(f))
        if cmds.getAttr("{}.uvTilingMode".format(f)):
            texture = re.sub("\.[0-9][0-9][0-9][0-9]\.", ".<UDIM>.", texture)
        file_texture_dict[f] = texture
    return file_texture_dict


def set_texture(file_node, texture):
    if os.path.exists(texture) or texture.find("UDIM") > -1:
        color_space = cmds.getAttr("{}.colorSpace".format(file_node))
        cmds.setAttr("{}.fileTextureName".format(file_node), texture, type="string")
        cmds.setAttr("{}.colorSpace".format(file_node), color_space, type="string")


def get_file_node_colorspace(file_node):
    color_space = cmds.getAttr("{}.colorSpace".format(file_node), asString=True)
    return color_space


#####################
def getUvShellList(name):
    # From https://polycount.com/discussion/196753/maya-python-get-a-list-of-all-uv-shells-in-a-selected-object
    selList = om.MSelectionList()
    selList.add(name)
    selListIter = om.MItSelectionList(selList, om.MFn.kMesh)
    pathToShape = om.MDagPath()
    selListIter.getDagPath(pathToShape)
    meshNode = pathToShape.fullPathName()
    uvSets = cmds.polyUVSet(meshNode, query=True, allUVSets=True)
    allSets = []
    for uvset in uvSets:
        shapeFn = om.MFnMesh(pathToShape)
        shells = om.MScriptUtil()
        shells.createFromInt(0)
        nbUvShells = shells.asUintPtr()

        uArray = om.MFloatArray()  # array for U coords
        vArray = om.MFloatArray()  # array for V coords
        uvShellIds = om.MIntArray()  # The container for the uv shell Ids

        shapeFn.getUVs(uArray, vArray)
        shapeFn.getUvShellsIds(uvShellIds, nbUvShells, uvset)

        shells = {}
        for i, n in enumerate(uvShellIds):
            if n in shells:
                shells[n].append([uArray[i], vArray[i]])
            else:
                shells[n] = [[uArray[i], vArray[i]]]
        allSets.append({uvset: shells})
    return allSets

def get_faces_with_flipped_uvs(node):
    faces = cmds.ls("{}.f[*]".format(node), flatten=1)
    flipped_faces = []

    for face in faces:
        uvs = []
        vtx_faces = cmds.ls(cmds.polyListComponentConversion(face, toVertexFace=True), flatten=True)
        for vtx_face in vtx_faces:
            uv = cmds.polyListComponentConversion(vtx_face, fromVertexFace=True, toUV=True)
            uvs.append(uv[0])
        # get edge vectors and cross them to get the uv face normal
        uv_a_pos = cmds.polyEditUV(uvs[0], q=1)
        uv_b_pos = cmds.polyEditUV(uvs[1], q=1)
        uv_c_pos = cmds.polyEditUV(uvs[2], q=1)
        uv_ab = imath.V2f(uv_b_pos[0] - uv_a_pos[0], uv_b_pos[1] - uv_a_pos[1]).normalize()
        uv_bc = imath.V2f(uv_c_pos[0] - uv_b_pos[0], uv_c_pos[1] - uv_b_pos[1]).normalize()
        if uv_ab.cross(uv_bc) < 0:
            flipped_faces.append(face)
    return flipped_faces
