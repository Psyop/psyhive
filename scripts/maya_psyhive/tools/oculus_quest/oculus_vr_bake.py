import functools
import json
import glob
import os
import pprint
import re
import sys

from maya import cmds

import abstract_maya
import cframe
import houdini_comp
import texture_convert

from psyhive import qt, tk, host
from psyhive.qt import QtUiTools, QtCore, QtGui, QtWidgets, Qt
from psyhive.utils import File, dprint, abs_path

FPS = "75fps"

OCULUS_BBOX = "OCULUS_BBOX"
CENTER_CAM = "CENTER_CAM"

# TODO: create mechanism to target UVs more finely.  Separate UI to specify UV percentage
# TODO: write all vrscenes and render all for background rendering, versus writing the vrscenes before each render
# TODO: Upgrade "skip existing" to be a listwidget
# TODO: Change background render to not lock up the foreground.
    # Update UI to be separate file, or change UI to be UI file (better)

# Source is where the geo comes from and provides the shading and full geometry for the color bake.
# Bake is where the UVs are baked.  This needs to have combined UVs for pieces, even those with animation.
# Export is where the final geometry is exported for unreal.  This can have more, separated pieces than the "Bake"
# group to accommodate things like animation.

SOURCE = "SOURCE"
SOURCE_STATIC = "SOURCE_STATIC"
SOURCE_ANIM = "SOURCE_ANIM"
SOURCE_SHADE_ONLY = "SOURCE_SHADE_ONLY"

BAKE = "BAKE"
BAKE_STATIC = "BAKE_STATIC"
BAKE_ANIM = "BAKE_ANIM"

EXPORT = "EXPORT"
EXPORT_STATIC = "EXPORT_STATIC"
EXPORT_ANIM = "EXPORT_ANIM"

DIFFUSE_PREFIX = "default"
REFLECTION_PREFIX = "reflection"

BAKE_GEO_ATTR = "bakeGeoType"

##### DECORATOR #####
# def catch_error(f):
#     @functools.wraps(f)
#     def catch_error_internal(*args, **kwargs):
#         try:
#             result = f(*args, **kwargs)
#             return result
#         except Exception, e:
#             import traceback
#             tb_string = traceback.format_exc()
#             message = e.message
#             message += "\n#####################\n"
#             message += tb_string
#             QtWidgets.QMessageBox.warning(None, "Error", message)
#             raise e
#     return catch_error_internal


def create_mipmap_textures(source_texture, mipmap_texture, colorspace, force=False):
    mipmap_dir = os.path.dirname(mipmap_texture)
    ext = os.path.splitext(source_texture)[-1].lower()[1:]

    if source_texture.find("<UDIM>") > -1:
        textures = glob.glob(source_texture.replace("<UDIM>", "*"))
        search = "\.[0-9][0-9][0-9][0-9]\.{}".format(ext)
        textures = [t for t in textures if re.search(search, t.lower())]
    else:
        textures = glob.glob(source_texture)

    if textures and not os.path.exists(mipmap_dir):
        os.mkdir(mipmap_dir)
    textures = [t.replace("\\", "/") for t in textures]

    source_texture_match_str = source_texture.lower().replace("<udim>", "(?P<udim>[0-9][0-9][0-9][0-9])?")
    source_texture_match = re.compile(source_texture_match_str)
    mipmap_texture_mask = mipmap_texture.replace("<UDIM>", "{udim}")

    for texture in textures:
        udim = source_texture_match.match(texture.lower()).groupdict().get("udim", "")
        mm_texture = mipmap_texture_mask.format(udim=udim)

        if os.path.exists(mm_texture):
            if force:
                os.remove(mm_texture)
            else:
                # If it's already mipped and the mip file is newer than the texture, continue
                texture_timestamp = os.path.getmtime(texture)
                mipmap_timestamp = os.path.getmtime(mm_texture)
                if texture_timestamp < mipmap_timestamp:
                    continue
        print "## Converting '{}' -> '{}'".format(texture, mm_texture)
        sys.stdout.flush()
        texture_convert.mipmap_texture(texture, mm_texture, colorspace)

    if textures:
        return True
    else:
        return False


def get_mipmap_texture_for_map(source_texture):
    mipmap_extension = "tif"
    mipmap_dir = "{}/mipmap".format(os.path.dirname(source_texture))
    mipmap_texture = "{}/{}.{}".format(mipmap_dir, os.path.splitext(os.path.basename(source_texture))[0],
                                           mipmap_extension)
    mipmap_texture = mipmap_texture.replace("\\", "/")
    return mipmap_texture


def get_non_mipmap_texture_for_map(texture):
    original_texture_format = "png"
    texture = texture.replace("\\", "/")
    texture = os.path.splitext(texture)[0] + "." + original_texture_format
    texture = texture.replace("mipmap/", "")
    return texture


def swap_mipmap_textures(mipmap=True):
    file_texture_dict = abstract_maya.get_file_texture_dict()
    for file_node, source_texture in file_texture_dict.iteritems():
        source_texture = source_texture.replace("//", "/")
        source_texture = source_texture.replace("\\", "/")
        source_texture = "/" + source_texture

        if mipmap:
            texture = get_mipmap_texture_for_map(source_texture)
        else:
            texture = get_non_mipmap_texture_for_map(source_texture)

        if os.path.exists(texture) or texture.find("<UDIM>") > -1:
            abstract_maya.set_texture(file_node, texture)


def mipmap_textures(force=False):
    file_texture_dict = abstract_maya.get_file_texture_dict()
    for file_node, source_texture in file_texture_dict.iteritems():
        if re.search("mipmap", source_texture) or re.search("BAKE", source_texture) or not source_texture.endswith("png"):
            continue
        if not os.path.exists(os.path.dirname(source_texture)):
            continue
        mipmap_texture = get_mipmap_texture_for_map(source_texture)
        colorspace = abstract_maya.get_file_node_colorspace(file_node)
        retval = create_mipmap_textures(source_texture, mipmap_texture, colorspace, force=force)
        if retval:
            print "Swapping {} -> {}".format(source_texture, mipmap_texture)
    swap_mipmap_textures(mipmap=True)


def get_bake_preset_dir():
    presets_dir = os.path.join(
        os.path.dirname(__file__),
        "resources",
    )
    return presets_dir


def get_ui_file_dir():
    ui_file_dir = os.path.join(os.path.dirname(__file__),  "ui_files")
    return ui_file_dir


def get_uipath(ui_file):
    """
    Returns an absolute path to the ui file
    :param ui_file: ui filename
    :return: full path to ui file
    :rtype: str
    """
    uibase = get_ui_file_dir()
    uipath = os.path.join(uibase, ui_file)
    return uipath


def get_bake_preset(name):
    """
    Each environment name can have centrally stored preferences.  These are serialized into JSON and read into here,
    whcih makes it easier to support bakes for multiple environments at once.

    Args:
        environment (str): String to lookup the environment.

    Returns:
        dict: dictionary with preferences
    """
    print 'GET PRESET', name
    presets_dir = get_bake_preset_dir()
    default_presets_file = os.path.join(presets_dir, "default.json")
    presets_file = os.path.join(presets_dir, name + ".json")
    return_dict = {}
    for each_file in [default_presets_file, presets_file]:
        if os.path.exists(each_file):
            with open(each_file) as json_file:
                return_dict.update(json.load(json_file))
    return return_dict


def get_bake_preset_names():
    presets_dir = get_bake_preset_dir()
    preset_names = [os.path.splitext(p)[0] for p in os.listdir(presets_dir)]
    print 'READ PRESET NAMES', preset_names
    return preset_names


def reset_outliner_order():
    """
    Organize things in order
    Returns:
        None
    """
    order_list = [
        CENTER_CAM,
        OCULUS_BBOX,
        SOURCE,
        BAKE,
        EXPORT,
    ]
    abstract_maya.set_outliner_order(order_list)


def parent_nodes_based_on_attributes():
    attr = BAKE_GEO_ATTR
    attr_parent_dict = abstract_maya.get_attr_value_for_all_nodes(attr)
    for node, parent in attr_parent_dict.iteritems():
        if abstract_maya.node_exists(node):
            top_parent = abstract_maya.get_top_parent(node)
            if not top_parent in [SOURCE, BAKE, EXPORT]:
                abstract_maya.parent_node(node, parent)


def create_bake_node_structure():
    """
    Create new nodes to provide structure for the bake process
    Returns:
        None
    """
    node_parent_list = [
        #[name, parent],
        [SOURCE, None],
        [SOURCE_STATIC, SOURCE],
        [SOURCE_ANIM, SOURCE],
        [SOURCE_SHADE_ONLY, SOURCE],
        [BAKE, None],
        [EXPORT, None],
    ]
    abstract_maya.create_node_hierarchy(node_parent_list)
    abstract_maya.hide_object(SOURCE_ANIM)


def create_bake_structure(center, width, height, depth, near_clip, far_clip):
    """
    Setup all components to bake

    Args:
        center (list): triplet with the center camera position
    Returns:
        None
    """
    abstract_maya.set_fps(FPS)
    abstract_maya.set_frame_range_to_anim_extent()
    print 'CREATE BBOX', OCULUS_BBOX, width, height, depth
    abstract_maya.create_bbox(OCULUS_BBOX, width, height, depth)
    abstract_maya.create_camera(CENTER_CAM, focal_length=12, translation=center,
                               lock_translation=True, near_clip=near_clip, far_clip=far_clip)
    create_bake_node_structure()
    abstract_maya.set_visibility_options(BAKE)
    abstract_maya.set_visibility_options(EXPORT)
    reset_outliner_order()


def apply_texel_scale(node, center, texel_density, distance_clamp):
    """
    Apply texel scale to the given node

    Args:
        node: name of the maya node

    Returns:
        None
    """
    nodes = abstract_maya.get_mesh_children(node)

    # Sets the texel density
    #   Sets the UVs to be based off of a relative viewpoint so textures look good in screen_space
    abstract_maya.set_relative_texel_density(nodes, center, texel_density, distance_clamp=distance_clamp)


def assign_comp_textures(output_directory):
    oculus_format = "png"
    node_group_dict = get_node_group_members()

    for node_group in sorted(node_group_dict.keys()):
        texture_name = get_file_texture_name(node_group, "*", "comp", output_directory, oculus_format)
        texture_match = (glob.glob(texture_name) or [None])[-1]
        bake_nodes = node_group_dict.get(node_group)
        if texture_match:
            for node in bake_nodes:
                abstract_maya.create_material_network(node_group, texture_match, assign_to=node)


def assign_baked_textures(resolution, output_directory, image_format):
    """
    Assuming textures were already baked, assign them to the node

    Args:
        node (str): Maya node

    Returns:
        None
    """
    node_group_dict = get_node_group_members()

    for node_group in sorted(node_group_dict.keys()):
        bake_nodes = node_group_dict.get(node_group)
        texture_name = get_file_texture_name(node_group, resolution, "default", output_directory, image_format)
        for node in bake_nodes:
            abstract_maya.create_material_network(node_group, texture_name, assign_to=node)


def get_file_version():
    """
    Return version string from the current file name
    Returns:
        str: version string
    """
    filename = get_file_base()
    match = re.search("_(?P<version>v[0-9]+(\.[0-9]+)*)$", filename)
    if match:
        version = match.group("version")
    else:
        version = "unknown"
    return version


def get_file_base():
    """
    Return version string from the current file name
    Returns:
        str: version string
    """
    filename = abstract_maya.get_current_file_name()
    version = os.path.splitext(os.path.basename(filename))[0]
    return version


def clear_preferences():
    abstract_maya.clear_preferences()


def save_work_file_to_output_directory(output_directory, force=True):
    # current_file = abstract_maya.get_current_file_name()
    _cur_work = tk.cur_work()
    print 'SAVE WORK FILE'
    print ' - OUTPUT DIR', output_directory
    output_file = get_output_file(output_directory)
    print ' - OUTPUT FILE', output_file
    if force or not os.path.exists(output_file):
        host.save_as(output_file)
        print ' - SAVED', output_file


def get_output_file(output_directory):
    # output_base = os.path.basename(output_directory)
    i = 0
    while True:
        output_file = "{}/work_{:04d}.mb".format(
            output_directory, i)
        # output_file = os.path.join(output_directory, output_file)
        if not os.path.exists(output_file):
            break
        i += 1
    # output_file = output_file.replace("\\", "/")
    return output_file


def get_output_directory(version=None):
    """
    Gte the output directory
    Returns:
        str: output directory
    """
    # Get SHOT_ROOT from the env
    # output_directory_root = os.getenv("SHOT_ROOT")

    # # Get SHOT number from the env
    # shot = os.getenv("SHOT")

    # Extend the vrbake output root dir from SHOT_ROOT
    _work = tk.cur_work()
    return abs_path("{}/vrbake/{}".format(_work.dir, _work.basename))

    # output_directory_root = "{}/vrbake".format(
    #     os.path.dirname(_work.dir))

    # # Create the folder if it does not exist
    # if not os.path.exists(output_directory_root):
    #     os.mkdir(output_directory_root)

    # # Build dir base name
    # output_directory_name_base = "{}_vrbake_v".format(_work.basename)

    # # Determine the version to assign
    # if version == None:
    #     version_search = re.compile("{}(?P<version>[0-9]+)$".format(output_directory_name_base))
    #     existing_dirs = glob.glob("{}/{}*/*.*".format(output_directory_root, output_directory_name_base))
    #     existing_dirs = [os.path.dirname(d) for d in existing_dirs]
    #     existing_dirs = [d for d in existing_dirs if version_search.search(d)]
    #     if existing_dirs:
    #         highest_version = int(version_search.search(existing_dirs[-1]).group("version"))
    #         version = highest_version + 1
    #     else:
    #         version = 1

    # # Create the subdir
    # output_directory = "{}/{}{:03}".format(output_directory_root, output_directory_name_base, version)
    # if not os.path.exists(output_directory):
    #     os.mkdir(output_directory)


    # # Cleanup the path slashes
    # output_directory = output_directory.replace("\\", "/")
    # return output_directory


def get_file_texture_name(node, resolution, mode, output_directory, image_format):
    """
    Get the target file texture name for a bake from the given node
    Args:
        node (str): Maya node name
        resolution (int): output resolution

    Returns:
        str: output bake texture name for node
    """
    if not node.startswith(get_bake_prefix()):
        node = "{}_0000".format(get_bake_prefix())

    if not os.path.exists(output_directory):
        try:
            os.mkdir(output_directory)
        except WindowsError as we:
            print we

    filename = get_file_base()
    os.path.basename(filename)
    filebase = os.path.splitext(filename)[0]

    file_texture_name = "{}/{}_{}_{}_{}.{}".format(
        output_directory,
        mode,
        filebase,
        node,
        resolution,
        image_format,
    )
    return file_texture_name


def get_latlong_name(output_directory, resolution, image_format):
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    filename = get_file_base()
    os.path.basename(filename)
    filebase = os.path.splitext(filename)[0]

    file_texture_name = "{}/latlong_{}_{}.{}".format(
        output_directory,
        filebase,
        resolution,
        image_format,
    )
    return file_texture_name


def get_qc_render_name(output_directory, resolution, image_format):
    if not os.path.exists(output_directory):
        os.mkdir(output_directory)

    filename = get_file_base()
    os.path.basename(filename)
    filebase = os.path.splitext(filename)[0]

    file_texture_name = "{}/qcrender_{}_{}.{}".format(
        output_directory,
        filebase,
        resolution,
        image_format,
    )
    return file_texture_name


def get_bake_prefix():
    """
    Get the name prefix for bake nodes

    Returns:
        str: Prefix for BAKE maya node names
    """
    return "{}".format(BAKE)


def combine_objects_into_uv_groups(map_count):
    """
    Args:
        center (list): list with point info, e.g. [0, 0, 0]

    Returns:
        list: Object groups created
    """
    children = abstract_maya.get_children(BAKE_STATIC)
    #abstract_maya.add_prefix(children, "temp_")

    objects = abstract_maya.get_mesh_children(BAKE_STATIC)
    anim_objects = abstract_maya.get_mesh_children(BAKE_ANIM)

    uv_area_list = [abstract_maya.get_uv_area(o) for o in objects]
    anim_uv_area = sum([abstract_maya.get_uv_area(o) for o in anim_objects])
    total_uv_area = sum(uv_area_list) + anim_uv_area
    uv_area_per_map = total_uv_area / float(map_count)

    object_uv_area_list = zip(objects, uv_area_list)
    object_uv_area_list = sorted(object_uv_area_list, key=lambda x:x[1], reverse=True)
    object_group_list = []
    uv_map_area = []
    for i in range(0, map_count):
        uv_map_area.append(0)
        object_group_list.append([])

    # Offset by the anim area, which always goes in index 0, and add the smallest object so there's always SOMETHING
    # in the space.
    uv_map_area[0] = anim_uv_area
    uv_map_area[0] += object_uv_area_list[-1][1]
    object_group_list[0].append(object_uv_area_list[-1][0])
    object_uv_area_list = object_uv_area_list[:-1]

    uv_map_index = 1 % map_count
    for node, uv_area in object_uv_area_list:
        start_index = uv_map_index
        miss = False
        while 1:
            if uv_map_area[uv_map_index] + uv_area < uv_area_per_map or miss and start_index == uv_map_index:
                uv_map_area[uv_map_index] += uv_area
                object_group_list[uv_map_index].append(node)
                uv_map_index = (uv_map_index + 1) % map_count
                break
            else:
                miss = True
            uv_map_index = (uv_map_index + 1) % map_count

    bake_prefix = get_bake_prefix()
    abstract_maya.delete_empty_child_groups(BAKE_STATIC)
    for i, object_group in enumerate(object_group_list):
        if not object_group:
            continue
        abstract_maya.group_objects(object_group, "{}_{:04d}".format(bake_prefix, i), BAKE_STATIC)
    abstract_maya.delete_empty_child_groups(BAKE_STATIC)
    return object_group_list


def create_bake_geometry():
    """
    Create a copy of the source geometry for the bake

    Returns:
        None
    """
    abstract_maya.delete_nodes([BAKE])
    abstract_maya.disable_screen_space_ambient_occlusion()

    abstract_maya.triangulate_objects(SOURCE)
    abstract_maya.delete_extra_uv_sets(SOURCE)
    abstract_maya.delete_hidden_children(SOURCE_STATIC)
    abstract_maya.delete_hidden_children(SOURCE_SHADE_ONLY)
    abstract_maya.delete_children_with_string_match(SOURCE, "_kill_")
    abstract_maya.delete_history(SOURCE, nondeformer_only=True)

    abstract_maya.create_group(BAKE)
    abstract_maya.duplicate_node(SOURCE_STATIC, BAKE_STATIC, parent=BAKE)
    node = abstract_maya.duplicate_node(SOURCE_ANIM, BAKE_ANIM, parent=BAKE, upstream_nodes=True, visible=True)
    abstract_maya.disable_skin_clusters(node)

    abstract_maya.delete_vertex_colors(BAKE)
    # abstract_maya.assign_checker_material(BAKE)
    # abstract_maya.assign_mipmap_debug_material(BAKE)
    reset_outliner_order()


def create_export_geometry():
    # type: () -> None
    """

    """
    abstract_maya.delete_nodes([EXPORT, EXPORT_STATIC, EXPORT_ANIM])
    abstract_maya.create_group(EXPORT)

    abstract_maya.delete_empty_child_groups(BAKE_STATIC)
    abstract_maya.duplicate_node(BAKE_STATIC, EXPORT_STATIC, parent=EXPORT, upstream_nodes=False)
    abstract_maya.combine_children(EXPORT_STATIC)
    node = abstract_maya.duplicate_node(BAKE_ANIM, EXPORT_ANIM, parent=EXPORT, upstream_nodes=True)

    abstract_maya.enable_skin_clusters(node)
    abstract_maya.delete_history(node, nondeformer_only=True)
    abstract_maya.set_visibility_options(EXPORT)
    reset_outliner_order()


def get_node_group_members():
    node_group_dict = {}
    bake_groups = [bg.split("|")[-1] for bg in abstract_maya.get_children(BAKE_STATIC)]
    bake_groups = [bake_group for bake_group in bake_groups if bake_group.find(get_bake_prefix()) > -1]
    for bake_group in bake_groups:
        bake_nodes = abstract_maya.get_mesh_children(bake_group)
        if bake_group.endswith("0"):
            anim_nodes = abstract_maya.get_mesh_children(BAKE_ANIM)
            bake_nodes = bake_nodes + anim_nodes
        else:
            bake_nodes = bake_nodes
        node_group_dict[bake_group] = bake_nodes
    return node_group_dict


def layout_uvs_for_bake_geometry_groups(resolution):
    """
    Layout the UVs for all bake geometry groups.  Note that any animated geometry is automatically laid out with the
    first group.

    Returns:
        None
    """
    node_group_dict = get_node_group_members()
    for node_group in sorted(node_group_dict.keys()):
        bake_nodes = node_group_dict.get(node_group)
        abstract_maya.layout_uvs_for_nodes(bake_nodes, resolution=resolution)


def get_bake_modes(do_reflection=False):
    bake_modes = [DIFFUSE_PREFIX]
    if do_reflection:
        bake_modes.append(REFLECTION_PREFIX)
    return bake_modes


def get_file_textures(output_directory, bake_reflection, resolution, image_format):
    node_group_dict = get_node_group_members()
    bake_modes = get_bake_modes(bake_reflection)

    texture_list = []
    for node_group in sorted(node_group_dict.keys()):
        for mode in bake_modes:
            texture_name = get_file_texture_name(node_group, resolution, mode, output_directory, image_format)
            texture_name.replace("\\", "/")
            texture_list.append(texture_name)
    return texture_list


def bake_textures(resolution, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult, output_directory,
                  image_format, do_reflection=False, map_list=None,
                  use_default_material=False, edge_padding=5):
    """

    Returns:

    """
    abstract_maya.set_renderable_camera(CENTER_CAM)
    abstract_maya.set_visibility_options(BAKE)
    abstract_maya.delete_children(EXPORT)
    abstract_maya.hide_object(SOURCE_ANIM)
    node_group_dict = get_node_group_members()

    _bake_modes = get_bake_modes(do_reflection)
    _fails = []
    for node_group in qt.progress_bar(sorted(node_group_dict)):

        _bake_nodes = node_group_dict.get(node_group)
        print 'BAKE NODES', _bake_modes

        # Get export paths
        _default_file = None
        _spec_file = None
        for _mode in _bake_modes:
            if _mode == 'default':
                _default_file = get_file_texture_name(
                    node_group, resolution, 'default', output_directory,
                    image_format)
            elif _mode == 'reflection':
                _spec_file = get_file_texture_name(
                    node_group, resolution, 'reflection', output_directory,
                    image_format)
            else:
                raise ValueError(_mode)

        # if map_list is not None and _default_file not in map_list:
        #     print("Skipping because unchecked: '{}' ...".format(_default_file))
        #     continue

        # Execute bake
        _texs = abstract_maya.bake_textures(
            node_group, _bake_nodes, default_file=_default_file,
            resolution=resolution, spec_file=_spec_file)
        if not _texs:
            _fails.append([node_group, _default_file])

    if _fails:
        pprint.pprint(_fails)
        qt.notify('Failed to generate {:d} textures'.format(len(_fails)))


def render_latlong(position, resolution, min_shading_rate, max_subdivs, admc_threshold, local_subdivs_mult,
                   output_directory, image_format, use_default_material, stereo_latlong, render_cube_map):
    output_file = get_latlong_name(output_directory, resolution, image_format)
    abstract_maya.render_latlong(position, output_file, resolution, min_shading_rate, max_subdivs, admc_threshold,
                                local_subdivs_mult, image_format, use_default_material, stereo_latlong, render_cube_map)


def qc_render(position, resolution, fov, min_shading_rate, max_subdivs, admc_threshold,
                   output_directory, image_format):
    output_file = get_qc_render_name(output_directory, resolution, image_format)
    abstract_maya.qc_render(position, output_file, resolution, fov, min_shading_rate, max_subdivs, admc_threshold,
                                image_format)

@abstract_maya.print_func_name
def delete_occluded_faces(
        node,
        center,
        height,
        near_clip,
        far_clip,
        horizontal_steps=4,
        vertical_steps=1,
        manual_points=[]
    ):

    """
    Delete faces occluded from the oculus area

    Returns:
        None
    """
    # Camera Settings
    abstract_maya.turn_on_double_sided()

    # Get the meshes we are working with
    nodes = abstract_maya.get_mesh_children(node)

    # Create a list of viewpoints
    view_points = abstract_maya.get_points_for_hemisphere(center, height, horizontal_steps, vertical_steps)
    view_points.extend(manual_points)

    # Do the deletion
    abstract_maya.delete_occluded_faces(nodes, view_points, near_clip=near_clip, far_clip=far_clip)


def save_preferences(**kwargs):
    """
    Store dictionary of prefs in current scene
    Args:
        **preferences:

    Returns:

    """
    preferences = abstract_maya.get_preferences("vrbake")
    for k, v in kwargs.iteritems():
        preferences[k] = v
    abstract_maya.set_preferences("vrbake", **preferences)


def load_preferences():
    """
    Return dictionary of prefs
    Returns:

    """
    preferences = abstract_maya.get_preferences("vrbake")
    return preferences


@abstract_maya.print_func_name
def composite_maps(output_directory, resolution, image_format, reflection_mix, bake_reflection):
    print "COMPOSITING MAPS:\n"
    output_format = "png"
    if not bake_reflection:
        reflection_mix = 0.0
    maps = [t for t in get_file_textures(output_directory, False, resolution, image_format) if os.path.exists(t)]
    map_conversion_list = []
    for diffuse_map in maps:
        if diffuse_map.find("/{}_".format(DIFFUSE_PREFIX)) > -1:
            reflection_map = re.sub(DIFFUSE_PREFIX, REFLECTION_PREFIX, diffuse_map)
            if os.path.exists(reflection_map) or not bake_reflection:
                if not bake_reflection:
                    reflection_map = diffuse_map
                output_map = re.sub(DIFFUSE_PREFIX, "comp", diffuse_map)
                output_map = os.path.splitext(output_map)[0] + "." + output_format
                map_conversion_list.append([diffuse_map, reflection_map, output_map])

    # Call to houdini to comp maps
    result = houdini_comp.houdini_comp(map_conversion_list, reflection_mix)
    return result


@abstract_maya.print_func_name
def export_fbx(output_directory, preset):
    version = get_file_version()
    basename = "{}_{}.{}.fbx".format(preset, version, "{subversion:04d}")
    output_file_mask = os.path.join(
        output_directory,
        basename
    )
    subversion = 1
    while 1:
        output_file = output_file_mask.format(subversion=subversion)
        if not os.path.exists(output_file):
            break
        subversion += 1
    print "Exporting '{}'".format(output_file)
    abstract_maya.export_fbx(EXPORT, output_file)


class QListWidgetItemTextureMap(QtWidgets.QListWidgetItem):
    def __init__(self, *args, **kwargs):
        super(QListWidgetItemTextureMap, self).__init__(*args, **kwargs)


class MayaOptimizeUV(QtWidgets.QMainWindow):
    def __init__(
            self,
            parent,
            resolution,
            min_shading_rate,
            max_subdivs,
            admc_threshold,
            local_subdivs_mult,
            preset_name,
            bake_reflection,
            map_count,
            skip_existing_maps,
            output_directory,
            horizontal_steps,
            vertical_steps,
            image_format,
            reflection_mix,
            use_default_material,
            stereo_render,
            edge_padding,
            render_cube_map
    ):
        super(self.__class__, self).__init__(parent)

        self.properties = [
            "admc_threshold",
            "bake_reflection",
            "edge_padding",
            "horizontal_steps",
            "image_format",
            "local_subdivs_mult",
            "map_count",
            "max_subdivs",
            "min_shading_rate",
            "output_directory",
            "preset_name",
            "reflection_mix",
            "render_cube_map",
            "resolution",
            "skip_existing_maps",
            "stereo_render",
            "use_default_material",
            "vertical_steps",
        ]

        # Using an env variable makes the path more generic, but use whatever you want
        self.settings_path = os.path.join(os.getenv('HOME'), "{}.ini".format(self.__class__.__name__))
        print 'SETTINGS PATH', self.settings_path

        # Restore window's previous geometry from file
        if os.path.exists(self.settings_path):
            settings_obj = QtCore.QSettings(self.settings_path, QtCore.QSettings.IniFormat)
            print 'RESTORING WINDOW GEOMETRY', settings_obj.value("windowGeometry")
            self.restoreGeometry(settings_obj.value("windowGeometry"))
            self.move(self.pos()+QtCore.QPoint(8, 31))

        self.setWindowFlags(Qt.Window)

        # Dynamic UI Load
        uifile = get_uipath("bake_ui3.ui")
        self.ui = QtUiTools.QUiLoader().load(uifile)
        self.setCentralWidget(self.ui)
        self.ui.show()

        # Bake Options -----------------------------------------------------
        self.bakeOptions = cframe.MayaFrameWidget(name="Bake Options", state=True, win=self, ui=get_uipath("bake_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.bakeOptions)

        self.bakeOptions.ui.bake_resolution_combo.addItems(["256", "512", "1024", "2048", "4096", "8192"])
        self.bakeOptions.ui.bake_resolution_combo.currentTextChanged.connect(self.update_output_files)

        self.bakeOptions.ui.bake_map_count_spinbox.setRange(1, 16)
        self.bakeOptions.ui.bake_map_count_spinbox.valueChanged.connect(self.update_output_files)
        self.bakeOptions.ui.bake_output_dir_increment_button.clicked.connect(self.update_output_directory)
        self.bakeOptions.ui.bake_preset_combo.addItems(get_bake_preset_names())
        self.bakeOptions.ui.bake_preset_combo.currentTextChanged.connect(self.load_preset)

        # Render Global Options ---------------------------------------
        self.render_global_options = cframe.MayaFrameWidget(name="Render Global Options", win=self, ui=get_uipath("render_global_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.render_global_options)

        self.render_global_options.ui.bake_min_shading_rate_spinbox.setRange(1, 16)
        self.render_global_options.ui.bake_max_subdivs_spinbox.setRange(1, 100)
        self.render_global_options.ui.bake_local_subdivs_mult_spinbox.setRange(1, 100)
        self.render_global_options.ui.bake_admc_threshold_spinbox.setRange(0.001, 1.0)

        self.min_shading_rate = min_shading_rate
        self.max_subdivs = max_subdivs
        self.admc_threshold = admc_threshold
        self.local_subdivs_mult = local_subdivs_mult

        # Geometry Occlusion Options ---------------------------------------
        self.geometry_occlusion_options = cframe.MayaFrameWidget(name="Geometry Occlusion Options", win=self, ui=get_uipath("geometry_occlusion_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.geometry_occlusion_options)

        self.geometry_occlusion_options.ui.bake_horizontal_steps_spinbox.setRange(1, 16)
        self.geometry_occlusion_options.ui.bake_vertical_steps_spinbox.setRange(1, 16)

        self.horizontal_steps = horizontal_steps
        self.vertical_steps = vertical_steps

        # Render Bake Options ---------------------------------------
        self.render_bake_options = cframe.MayaFrameWidget(name="Render Bake Options", win=self, ui=get_uipath("render_bake_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.render_bake_options)
        self.render_bake_options.ui.edge_padding_spinbox.setRange(0, 9)

        self.bake_reflection = bake_reflection
        self.skip_existing_maps = skip_existing_maps
        self.use_default_material = use_default_material
        self.edge_padding = edge_padding

        self.render_bake_options.ui.bake_reflection_checkbox.clicked.connect(self.update_output_files)
        self.render_bake_options.ui.bake_skip_existing_checkbox.clicked.connect(self.update_output_files)

        # Render LatLong Options ---------------------------------------
        self.render_latlong_options = cframe.MayaFrameWidget(name="Render LatLong Options", win=self, ui=get_uipath("render_latlong_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.render_latlong_options)

        self.stereo_render = stereo_render
        self.render_cube_map = render_cube_map

        # Map Composite Options ---------------------------------------
        self.map_composite_options = cframe.MayaFrameWidget(name="Map Composite Options", win=self, ui=get_uipath( "map_composite_options.ui"))
        self.ui.bake_tab_layout.addWidget(self.map_composite_options)
        self.map_composite_options.ui.bake_reflection_mix_spinbox.setRange(0, 1)
        self.reflection_mix = reflection_mix

        # Bake Execution ---------------------------------------
        self.bake_execution = cframe.MayaFrameWidget(name="Bake Execution", state=True, win=self, ui=get_uipath("bake_execution.ui"))
        self.ui.bake_tab_layout.addWidget(self.bake_execution)
        self.ui.bake_tab_layout.setAlignment(Qt.AlignTop)
        self.ui.bake_tab_layout.addStretch()
        self.ui.bake_tab_layout.setStretch(self.ui.bake_tab_layout.count()-1, 1)

        # Initialize bake settings for Bake Options
        self.output_directory = output_directory
        self.map_count = map_count
        self.resolution = resolution
        self.preset_name = preset_name
        self.image_format = image_format

        # Create Execute buttons
        self.create_execute_buttons()

        # Create Attribute buttons
        self.create_attribute_buttons()

        self.load_preferences()
        self.load_preset('default')
        self.update_output_files()

    def create_attribute_buttons(self):
        attr_buttons = []
        ########## ATTRIBUTE LAYOUT ################
        set_layout = self.ui.attr_set_layout
        set_type = self.set_bake_geo_type_attr
        sel_layout = self.ui.attr_select_layout
        sel_type = self.select_bake_geo_type_attr
        clr_layout = self.ui.attr_clear_layout
        clr_type = self.clear_bake_geo_type_attr

        button_list = [
            ["Set Static Attribute", set_layout, lambda x=set_type, t=SOURCE_STATIC: x(t), ""],
            ["Set Anim Attribute", set_layout, lambda x=set_type, t=SOURCE_ANIM: x(t), ""],
            ["Set Shade Only Attribute", set_layout, lambda x=set_type, t=SOURCE_SHADE_ONLY: x(t), ""],
            ["Select Static Attribute", sel_layout, lambda x=sel_type, t=SOURCE_STATIC: x(t), ""],
            ["Select Anim Attribute", sel_layout, lambda x=sel_type, t=SOURCE_ANIM: x(t), ""],
            ["Select Shade Only Attribute", sel_layout, lambda x=sel_type, t=SOURCE_SHADE_ONLY: x(t), ""],
            ["Clear Attribute on Selected", clr_layout, lambda x=clr_type: x(), ""],
        ]

        for [label, layout, function, tooltip] in button_list:
            button = QtWidgets.QPushButton(label)
            if tooltip:
                button.setToolTip(tooltip)
            if function:
                button.clicked.connect(function)
            layout.addWidget(button)
        return attr_buttons

    def create_execute_buttons(self):
        style = '''
            min-height: 1.3em;
            color: #bbbbbb;
            background-color: #51615d;
        '''

        style2 = '''QPushButton {
            background-color: #5a8176;
            min-height: 1.25em;
            border-radius: 12px;
            padding: 6px;
        }
            QPushButton:hover {
            background: qlineargradient(
            x1 : 0, y1 : 0, x2 : 0, y2 :   1,
            stop :   0.0 #679489,
            stop :   0.5 #70a195,
            stop :   0.55 #70a195,
            stop :   1.0 #679489);
        }
        '''

        style1 = '''QPushButton {
            background-color: #8fbfb5;
            color: #263631;
            border-radius: 12px;
            min-height: 2em;
            padding: 6px;
        }
            QPushButton:hover {
            background: qlineargradient(
            x1 : 0, y1 : 0, x2 : 0, y2 :   1,
            stop :   0.0 #7eb5a7,
            stop :   0.5 #a0d6ca,
            stop :   0.55 #a0d6ca,
            stop :   1.0 #7eb5a7);
        }
        '''

        button_list = [
            ["Create Bake Structure", lambda x=self.create_bake_structure_callback: x(),
                    "<html>Create parent nodes to classify bake, set frame range based on animation, create center "
                    "camera, "
                    "create oculus bounding box for scale reference.", style2],
            ["Setup Bake", self.setup_bake,
                    "<html>Triangulate source, duplicate source geometry to bake copy, deactivate deformers, "
                    "cull occluded "
                    "faces, resize UVs based on screen space from center of bounding box, divide geometry into the "
                    "number of top nodes specified by map count, lays out UVs for each one of the groups.", style2],
            ["Enable Mipmaps", lambda x=self.enable_mipmaps: x(), "", style],
            ["Disable Mipmaps", lambda x=self.disable_mipmaps: x(), "", style],
            ["Bake Shading and Lighting", lambda x=self.bake_textures: x(),
                    "<html>Uses arnold to bake the shading and lighting for "
                    "each of the top nodes, assigns the shaders to the bake "
                    "geometry, copies bake geometry to new 'EXPORT' geometry, "
                    "combines that geometry into fewer pieces and assigns "
                    "shaders to that as well, reactivates deformers for the "
                    "animations.", style2],
            ["Composite Maps", lambda x=self.composite_maps: x(),
                     "<html>Search for reflection maps and, if they exist, composite them together with diffuse.", style2],
            ["Export FBX", lambda x=self.export_fbx: x(),
                    "<html>Export an FBX file from the EXPORT group to the output directory.  The last number in the "
                    "file name wlil continuously ascend and not overwrite previous versions.", style1],
            ["Render Environment", lambda x=self.render_latlong: x(), "<html>", style],
            ["QC Render", lambda x=self.qc_render: x(), "<html>", style],
        ]

        # Populate Execution Layout with buttons
        button_widget_list = []
        for [label, function, tooltip, style_sheet] in button_list:
            button = QtWidgets.QPushButton(label)
            button.setToolTip(tooltip)
            button.clicked.connect(function)
            button.clicked.connect(self.save_preferences)
            button.setStyleSheet(style_sheet)
            button_widget_list.append(button)
            self.bake_execution.ui.bake_execution_layout.addWidget(button)

        self.bake_execution.ui.bake_execution_layout.addStretch(-1)

    @property
    def preset_name(self):
        return self.bakeOptions.ui.bake_preset_combo.currentText()

    @preset_name.setter
    def preset_name(self, value):
        self.bakeOptions.ui.bake_preset_combo.setCurrentText(str(value))

    @property
    def resolution(self):
        return int(self.bakeOptions.ui.bake_resolution_combo.currentText())

    @resolution.setter
    def resolution(self, value):
        self.bakeOptions.ui.bake_resolution_combo.setCurrentText(str(value))

    @property
    def map_count(self):
        return self.bakeOptions.ui.bake_map_count_spinbox.value()

    @map_count.setter
    def map_count(self, value):
        self.bakeOptions.ui.bake_map_count_spinbox.setValue(value)

    @property
    def local_subdivs_mult(self):
        return self.render_global_options.ui.bake_local_subdivs_mult_spinbox.value()

    @local_subdivs_mult.setter
    def local_subdivs_mult(self, value):
        self.render_global_options.ui.bake_local_subdivs_mult_spinbox.setValue(value)

    @property
    def max_subdivs(self):
        return self.render_global_options.ui.bake_max_subdivs_spinbox.value()

    @max_subdivs.setter
    def max_subdivs(self, value):
        self.render_global_options.ui.bake_max_subdivs_spinbox.setValue(value)

    @property
    def admc_threshold(self):
        return self.render_global_options.ui.bake_admc_threshold_spinbox.value()

    @admc_threshold.setter
    def admc_threshold(self, value):
        self.render_global_options.ui.bake_admc_threshold_spinbox.setValue(value)

    @property
    def horizontal_steps(self):
        return self.geometry_occlusion_options.ui.bake_horizontal_steps_spinbox.value()

    @horizontal_steps.setter
    def horizontal_steps(self, value):
        self.geometry_occlusion_options.ui.bake_horizontal_steps_spinbox.setValue(value)

    @property
    def vertical_steps(self):
        return self.geometry_occlusion_options.ui.bake_vertical_steps_spinbox.value()

    @vertical_steps.setter
    def vertical_steps(self, value):
        self.geometry_occlusion_options.ui.bake_vertical_steps_spinbox.setValue(value)

    @property
    def min_shading_rate(self):
        return self.render_global_options.ui.bake_min_shading_rate_spinbox.value()

    @min_shading_rate.setter
    def min_shading_rate(self, value):
        self.render_global_options.ui.bake_min_shading_rate_spinbox.setValue(value)

    @property
    def skip_existing_maps(self):
        return self.render_bake_options.ui.bake_skip_existing_checkbox.isChecked()

    @skip_existing_maps.setter
    def skip_existing_maps(self, value):
        self.render_bake_options.ui.bake_skip_existing_checkbox.setChecked(value)

    @property
    def bake_reflection(self):
        return self.render_bake_options.ui.bake_reflection_checkbox.isChecked()

    @bake_reflection.setter
    def bake_reflection(self, value):
        self.render_bake_options.ui.bake_reflection_checkbox.setChecked(value)

    @property
    def use_default_material(self):
        return self.render_global_options.ui.bake_use_default_material_checkbox.isChecked()

    @use_default_material.setter
    def use_default_material(self, value):
        self.render_global_options.ui.bake_use_default_material_checkbox.setChecked(value)

    @property
    def stereo_render(self):
        return self.render_latlong_options.ui.bake_stereo_render_checkbox.isChecked()

    @stereo_render.setter
    def stereo_render(self, value):
        self.render_latlong_options.ui.bake_stereo_render_checkbox.setChecked(value)

    @property
    def render_cube_map(self):
        return self.render_latlong_options.ui.bake_cube_map_checkbox.isChecked()

    @render_cube_map.setter
    def render_cube_map(self, value):
        self.render_latlong_options.ui.bake_cube_map_checkbox.setChecked(value)

    @property
    def output_directory(self):
        return self.bakeOptions.ui.bake_output_dir_text.text()

    @output_directory.setter
    def output_directory(self, value):
        self.bakeOptions.ui.bake_output_dir_text.setText(value)

    @property
    def image_format(self):
        # return self.ui.image_format_text.text()
        return self.bakeOptions.ui.image_format_combo.currentText()

    @image_format.setter
    def image_format(self, value):
        # self.ui.image_format_text.setText(value)
        self.bakeOptions.ui.image_format_combo.setCurrentText(str(value))

    @property
    def reflection_mix(self):
        return self.map_composite_options.ui.bake_reflection_mix_spinbox.value()

    @reflection_mix.setter
    def reflection_mix(self, value):
        self.map_composite_options.ui.bake_reflection_mix_spinbox.setValue(value)

    @property
    def edge_padding(self):
        return self.render_bake_options.ui.edge_padding_spinbox.value()

    @edge_padding.setter
    def edge_padding(self, value):
        self.render_bake_options.ui.edge_padding_spinbox.setValue(value)

    def set_bake_geo_type_attr(self, geotype):
        attr = BAKE_GEO_ATTR
        abstract_maya.set_string_attr_for_selected(attr, geotype, ad=False)

    def clear_bake_geo_type_attr(self):
        attr = BAKE_GEO_ATTR
        abstract_maya.delete_nodes_attr(attr)

    def select_bake_geo_type_attr(self, geotype):
        attr = BAKE_GEO_ATTR
        abstract_maya.select_nodes_with_attr_value(attr, geotype)

    def update_output_directory(self):
        output_directory = get_output_directory()
        self.output_directory = output_directory
        save_work_file_to_output_directory(self.output_directory, force=False)
        self.update_output_files()
        self.save_preferences()

    @abstract_maya.print_func_name
    def create_bake_structure_callback(self):
        self.create_bake_structure()
        parent_nodes_based_on_attributes()
        save_work_file_to_output_directory(self.output_directory, force=False)
        self.duplicate_to_export_grp()

    def duplicate_to_export_grp(self):
        _children = cmds.listRelatives('|SOURCE|SOURCE_STATIC', children=1, fullPath=1)
        if not _children:
            return
        print 'CHILDREN', _children
        _dup = cmds.duplicate(_children, returnRootsOnly=1)
        print 'DUP', _dup
        cmds.parent(_dup, '|EXPORT')

    def create_bake_structure(self):
        create_bake_structure(
            self.OCULUS_CENTER,                 # Loaded preset
            self.OCULUS_WIDTH,                  # Loaded preset
            self.OCULUS_HEIGHT,                 # Loaded preset
            self.OCULUS_DEPTH,                  # Loaded preset
            self.NEAR_CLIPPING_PLANE,           # Loaded preset
            self.FAR_CLIPPING_PLANE,            # Loaded preset
        )

    def get_active_map_list(self):
        map_list = []
        for i in range(0, self.render_bake_options.ui.bake_maps_to_bake_listwidget.count()):
            item = self.render_bake_options.ui.bake_maps_to_bake_listwidget.item(i)
            if item.checkState():
                map_list.append(str(item.text()))
        return map_list


    def render_latlong(self):
        render_latlong(
            self.OCULUS_CENTER,
            self.resolution,
            self.min_shading_rate,
            self.max_subdivs,
            self.admc_threshold,
            self.local_subdivs_mult,
            self.output_directory,
            self.image_format,
            self.use_default_material,
            self.stereo_render,
            self.render_cube_map
        )


    def qc_render(self):
        horizontal_resolution = 1280
        horizontal_fov = 110
        qc_render(
            self.OCULUS_CENTER,
            horizontal_resolution,
            horizontal_fov,
            self.min_shading_rate,
            self.max_subdivs,
            self.admc_threshold,
            self.output_directory,
            self.image_format
        )

    @abstract_maya.print_func_name
    @abstract_maya.keep_current_camera

    def bake_textures(self):
        try:
            self.create_bake_structure()
            map_list = self.get_active_map_list()
            bake_textures(self.resolution, self.min_shading_rate, self.max_subdivs, self.admc_threshold,
                          self.local_subdivs_mult, self.output_directory, self.image_format, self.bake_reflection,
                          map_list, self.use_default_material, self.edge_padding)
            self.bake_finished()
        except:
            self.update_output_files()
            raise

    def bake_finished(self):
        assign_baked_textures(self.resolution, self.output_directory, self.image_format)
        self.update_output_files()

    def update_output_files(self):
        output_files = get_file_textures(self.output_directory, self.bake_reflection, self.resolution,
                                         self.image_format)
        self.render_bake_options.ui.bake_maps_to_bake_listwidget.clear()

        for file in output_files:
            item = QListWidgetItemTextureMap()
            item.setText(file)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if self.skip_existing_maps and os.path.exists(file):
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            self.render_bake_options.ui.bake_maps_to_bake_listwidget.addItem(item)

    @abstract_maya.print_func_name
    @abstract_maya.keep_current_camera
    def setup_bake(self, struct=True, geo=True, occ=True, uv=True):
        # Auto-runs create bake structure
        if struct:
            dprint('CREATE BAKE STRUCTURE')
            self.create_bake_structure()

        # Duplicates the source Geometry
        if geo:
            dprint('CREATE BAKE GEOMETRY')
            create_bake_geometry()

        # Removes/optimizes faces based on Camera Occlusion
        if occ:
            dprint('DELETE OCCLUDED FACES')
            delete_occluded_faces(
                BAKE_STATIC,                                    # Name of the Bake Group
                self.OCULUS_CENTER,                             # Loaded preset
                self.OCULUS_HEIGHT,                             # Loaded preset
                self.NEAR_CLIPPING_PLANE,                       # Loaded preset
                self.FAR_CLIPPING_PLANE,                        # Loaded preset
                horizontal_steps=self.horizontal_steps,         # Horizontal Steps from UI SpinBox
                vertical_steps=self.vertical_steps,             # Vertical Steps from UI SpinBox
                manual_points=self.manual_points                # Loaded preset
            )
        if uv:
            # Set the UVs to be based off of a relative viewpoint
            dprint('APPLY TEXEL SCALE')
            apply_texel_scale(
                BAKE,
                self.OCULUS_CENTER,     # Loaded preset
                self.TEXEL_DENSITY,     # Loaded preset
                self.DISTANCE_CLAMP     # Loaded preset
            )

            # Build the UV Groups
            dprint('COMBINE OBJECTS INTO UV GROUPS')
            combine_objects_into_uv_groups(self.map_count)

            # Auot-layout UVs
            dprint('LAYOUT UVS FOR BAKE GEOMETRY GROUPS')
            layout_uvs_for_bake_geometry_groups(self.resolution)

            # Populate the output file list
            dprint('UPDATE OUTPUT FILES')
            self.update_output_files()

    def spherical_uvs(self):
        abstract_maya.create_spherical_uvs(BAKE, self.OCULUS_CENTER)

        # Crete UVs based on preset values
        apply_texel_scale(
            BAKE,
            self.OCULUS_CENTER,     # Loaded preset
            self.TEXEL_DENSITY,     # Loaded preset
            self.DISTANCE_CLAMP     # Loaded preset
        )
        combine_objects_into_uv_groups(self.map_count)
        layout_uvs_for_bake_geometry_groups(self.resolution)
        self.update_output_files()


    def enable_mipmaps(self):
        # Disable mipmaps first to force reevaluation of everything
        swap_mipmap_textures(False)
        mipmap_textures()


    def disable_mipmaps(self):
        swap_mipmap_textures(False)

    @abstract_maya.print_func_name
    @abstract_maya.keep_current_camera
    def composite_maps(self):
        create_export_geometry()
        result = composite_maps(self.output_directory, self.resolution, self.image_format, self.reflection_mix, self.bake_reflection)
        assign_comp_textures(self.output_directory)
        if not result:
            print "{:#^80}".format(" Compsite Maps Failed ")

    def export_fbx(self):
        export_fbx(self.output_directory, self.preset_name)

    def save_preferences(self):
        preferences_dict = {}
        for p in self.properties:
            preferences_dict[p] = eval("self.{}".format(p))
        save_preferences(**preferences_dict)

    def load_preferences(self):
        preferences_dict = load_preferences()
        for k, v in preferences_dict.iteritems():
            try:
                if type(v) in [str, unicode]:
                    v = "'{}'".format(v)
                command = "self.{} = {}".format(k, v)
                exec(command)
            except:
                import traceback
                traceback.print_exc()
                print("Cannot load preferences '{} = {}'".format(k, v))

    def load_preset(self, name=None):
        print 'LOAD PRESET', name
        required_presets = [
            "OCULUS_CENTER",
            "DISTANCE_CLAMP",
            "OCULUS_WIDTH",
            "OCULUS_DEPTH",
            "OCULUS_HEIGHT",
            "FAR_CLIPPING_PLANE",
            "NEAR_CLIPPING_PLANE",
            "TEXEL_DENSITY",
            "manual_points",
        ]
        if name == None:
            name = self.bakeOptions.ui.bake_preset_combo.currentText()
        if name != "default":
            self.preset_name = name
        self.bakeOptions.ui.bake_preset_combo.setCurrentText(name)

        preset_dict = get_bake_preset(name)
        for key in required_presets:
            if not key in preset_dict:
                raise Exception("Missing preset variable '{}'".format(key))

        for k, v in preset_dict.iteritems():
            self.__dict__[k] = v
            label_obj_name = '{}_data_label'.format(k)
            widget = self.geometry_occlusion_options.ui.findChildren(QtWidgets.QLabel, label_obj_name)
            if widget:
                label = widget[-1]
                label.setText(str(v))

    def closeEvent(self, event):
        settings_obj = QtCore.QSettings(self.settings_path, QtCore.QSettings.IniFormat)
        settings_obj.setValue("windowGeometry", self.saveGeometry())

        print "Closing '{}'".format(self.windowTitle())


########################
def _maya_main_window():
    """Return Maya's main window"""
    # widgets = QtWidgets.qApp.topLevelWidgets()

    # app = QtWidgets.QApplication(sys.argv)
    app = QtWidgets.QApplication.instance()
    widgets = app.topLevelWidgets()

    for obj in widgets:
        if obj.objectName() == 'MayaWindow':
            return obj
    raise RuntimeError('Could not find MayaWindow instance')


# def get_main_window():
#     ptr = OpenMayaUI.MQtUtil.mainWindow()
#     main_win = QtCompat.wrapInstance(long(ptr))
#     return main_win


def launch():
    preset_name = "default"
    image_format = "png"

    # Check for current work
    if not tk.cur_work():
        qt.notify_warning(
            'No current work file.\n\nPlease save your scene so '
            'the toolkit know where to export data to.',
            title='No work file')
        return

    filename_lower = get_file_base()
    for preset in get_bake_preset_names():
        if filename_lower.find(preset) > -1:
            preset_name = preset
            break

    output_directory = get_output_directory()
    # maya_window = get_main_window()
    maya_window = _maya_main_window()
    maya_optimize_uv = MayaOptimizeUV(
        parent=maya_window,
        resolution=4096,
        min_shading_rate=4,
        max_subdivs=8,
        admc_threshold=0.01,
        local_subdivs_mult=3,
        preset_name=preset_name,
        bake_reflection=True,
        map_count=3,
        skip_existing_maps=True,
        output_directory=output_directory,
        horizontal_steps=8,
        vertical_steps=3,
        image_format=image_format,
        reflection_mix=1,
        use_default_material=False,
        stereo_render=False,
        edge_padding=5,
        render_cube_map=True
    )

    maya_optimize_uv.setWindowTitle("{}".format("Oculus Quest Toolkit"))
    maya_optimize_uv.show()

    return maya_optimize_uv
