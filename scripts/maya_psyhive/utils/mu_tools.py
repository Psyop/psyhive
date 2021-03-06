"""General tools."""

import tempfile

from maya import cmds, mel
from maya.app.general import createImageFormats

import six

from psyhive import qt
from psyhive.utils import (
    get_single, lprint, File, dprint, get_path, Movie, Seq)

from .mu_const import COLS
from .mu_dec import restore_ns, get_ns_cleaner

_FPS_LOOKUP = {
    23.97: "film",
    23.98: "film",
    24.0: "film",
    25.0: "pal",
    29.97: "ntsc",
    30.0: "ntsc",
    48.0: "show",
    50.0: "palf",
    60.0: "ntscf"}


@restore_ns
def add_to_dlayer(obj, layer, verbose=0):
    """Add the specified object to a display layer, creating it if needed.

    Args:
        obj (str): object to add
        layer (str): layer to add to
        verbose (int): print process data
    """
    if not cmds.objExists(layer):
        set_namespace(":")
        dprint("Creating displaylayer", layer, verbose=verbose)
        cmds.createDisplayLayer(name=layer, number=True, empty=True)

    cmds.editDisplayLayerMembers(layer, obj, noRecurse=1)


@restore_ns
def add_to_grp(obj, grp):
    """Add the given object to the given group, creating it if required.

    Args:
        obj (str): object to add
        grp (str): name of group to add to
    """
    if not cmds.objExists(grp):
        cmds.namespace(set=':')
        cmds.group(name=grp, empty=True)
    if not get_parent(obj) == grp:
        cmds.parent(obj, grp)
    return grp


@restore_ns
def add_to_set(obj, set_, verbose=0):
    """Add the given object to the given set, creating it if required.

    Args:
        obj (str): object to add
        set_ (str): name of set to add to
        verbose (int): print process data
    """
    if not cmds.objExists(set_):
        lprint("SET DOES NOT EXIST:", set_, verbose=verbose)
        cmds.namespace(set=':')
        cmds.sets(name=set_, empty=True)
    cmds.sets(obj, addElement=set_)


def bake_results(chans, simulation=False, range_=None):
    """Bake anim on the given list of channels.

    Args:
        chans (str list): list of channels to bake
        simulation (bool): bake as simulation (scrub timeline)
        range_ (tuple): override bake range
    """
    from psyhive import host
    _range = range_ or host.t_range()
    cmds.bakeResults(chans, time=_range, simulation=simulation)


def blast(seq, range_=None, res=None, force=False, cam=None, view=False,
          verbose=0):
    """Execute a playblast.

    Args:
        seq (Seq): output sequence
        range_ (tuple): start/end frame
        res (tuple): override image resolution
        force (bool): overwrite existing images without confirmation
        cam (str): override camera
        view (bool): view blast on complete
        verbose (int): print process data
    """
    from psyhive import host
    from maya_psyhive import ui

    # Get res
    if res:
        _width, _height = res
        cmds.setAttr('defaultResolution.width', _width)
        cmds.setAttr('defaultResolution.height', _height)
    else:
        _width = cmds.getAttr('defaultResolution.width')
        _height = cmds.getAttr('defaultResolution.height')
    lprint('RES', _width, _height, verbose=verbose)

    # Get range
    _rng = range_ or host.t_range()
    _start, _end = _rng

    if cam:
        _panel = ui.get_active_model_panel()
        cmds.modelEditor(_panel, edit=True, camera=cam)

    seq.delete(wording='Replace', force=force)
    seq.test_dir()

    # Set image format
    _fmt_mgr = createImageFormats.ImageFormats()
    _fmt_mgr.pushRenderGlobalsForDesc({
        'jpg': "JPEG",
        'exr': "EXR",
    }[seq.extn])

    _filename = '{}/{}'.format(seq.dir, seq.basename)
    lprint('BLAST FILENAME', _filename, verbose=verbose)
    cmds.playblast(
        startTime=_start, endTime=_end, format='image', filename=_filename,
        viewer=False, width=_width, height=_height, offScreen=True,
        percent=100)
    assert seq.get_frames(force=True)

    _fmt_mgr.popRenderGlobals()

    if view:
        seq.view()


def blast_to_mov(mov, range_=None, res=None, force=False, cam=None, view=False,
                 verbose=0):
    """Playblast current scene to mov.

    Args:
        mov (str): path to mov file
        range_ (tuple): start/end frame
        res (tuple): override image resolution
        force (bool): overwrite existing file without confirmation
        cam (str): override camera
        view (bool): view blast on complete
        verbose (int): print process data
    """
    _mov = Movie(mov)
    _mov.delete(force=force)
    _tmp_seq = Seq('{}/blast_tmp.%04d.jpg'.format(tempfile.gettempdir()))
    blast(_tmp_seq, range_=range_, res=res, force=True, cam=cam, view=False,
          verbose=verbose)
    _tmp_seq.to_mov(_mov)
    if view:
        _mov.view()
    _tmp_seq.delete(force=True)


def break_conns(attr):
    """Break connections on the given attribute.

    Args:
        attr (str): name of attribute
    """
    _conns = cmds.listConnections(attr, destination=False)
    cmds.delete(_conns)


def create_attr(attr, value, keyable=True, update=True, locked=False,
                verbose=0):
    """Add an attribute.

    Args:
        attr (str): attr name (eg. persp1.blah)
        value (any): attribute value to apply
        keyable (bool): keyable state of attribute
        update (bool): update attribute to value provided
            (default is true)
        locked (bool): create attr as locked
        verbose (int): print process data

    Returns:
        (str): full attribute name (eg. persp.blah)
    """
    _node, _attr = attr.split('.')

    # Create attr
    _type = _class = None
    _created = False
    if not cmds.attributeQuery(_attr, node=_node, exists=True):
        if isinstance(value, qt.HColor):
            cmds.addAttr(
                _node, longName=_attr, attributeType='float3',
                usedAsColor=True)
            for _chan in 'RGB':
                print 'ADDING', _attr+_chan
                cmds.addAttr(
                    _node, longName=_attr+_chan, attributeType='float',
                    parent=_attr)
            _class = qt.HColor
        else:
            _kwargs = {
                'longName': _attr,
                'keyable': keyable,
            }
            if isinstance(value, six.string_types):
                _kwargs['dataType'] = 'string'
                _type = 'string'
            elif isinstance(value, float):
                _kwargs['attributeType'] = 'float'
                _kwargs['defaultValue'] = value
            elif isinstance(value, int):
                _kwargs['attributeType'] = 'long'
                _kwargs['defaultValue'] = value
            else:
                raise ValueError(value)
            lprint("ADDING ATTR", _node, _kwargs, verbose=verbose)
            cmds.addAttr(_node, **_kwargs)
        _created = True

    # Apply value
    _cur_val = get_val(attr, type_=_type, class_=_class)
    if not _cur_val == value and (_created or update):
        _kwargs = {}
        set_val(attr, value)

    if locked:
        cmds.setAttr(attr, lock=True)

    return attr


def cycle_check():
    """Check cycle check is disabled.

    Provided to avoid straight turning it off, which can be expensive.
    """
    if cmds.cycleCheck(query=True, evaluation=True):
        cmds.cycleCheck(evaluation=False)


@restore_ns
def del_namespace(namespace, force=True):
    """Delete the given namespace.

    Args:
        namespace (str): namespace to delete
        force (bool): delete nodes without confirmation
    """
    from maya_psyhive import ref

    if not cmds.namespace(exists=namespace):
        return

    _force = force
    _ref = ref.find_ref(namespace=namespace.lstrip(':'), catch=True)
    if _ref:
        _ref.remove(force=_force)
        _force = True

    if not _force:
        qt.ok_cancel(
            'Are you sure you want to delete the namespace {}?'.format(
                namespace))
    set_namespace(namespace, clean=True)
    set_namespace(":")
    cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)


def find_cams(orthographic=False):
    """List cameras in the scene.

    This is useful for py_gui camera lists.

    Args:
        orthographic (bool): include orthographic cams

    Returns:
        (str list): list of camera transforms
    """
    return [
        get_single(cmds.listRelatives(_cam, parent=True))
        for _cam in cmds.ls(type='camera')
        if orthographic or not cmds.getAttr(_cam+'.orthographic')]


def get_fps():
    """Get current frame rate.

    Returns:
        (float): fps
    """
    _unit = cmds.currentUnit(query=True, time=True)

    for _fps, _name in reversed(_FPS_LOOKUP.items()):
        if _fps in [23.98, 23.97, 29.97]:  # Ignore values that confuse maya
            continue
        if _unit == _name:
            return _fps

    try:
        return float(_unit.replace("fps", ""))
    except ValueError:
        pass

    raise RuntimeError("Unknown maya time unit: "+_unit)


def get_parent(node):
    """Get parent of the given node.

    Args:
        node (str): node to read

    Returns:
        (str): parent node
    """
    _parents = cmds.listRelatives(node, parent=True, path=True) or []
    return get_single(_parents, catch=True)


def get_shp(node, verbose=0):
    """Get the shape of the given node.

    Args:
        node (str): node to read
        verbose (int): print process data

    Returns:
        (str): shape node
    """
    _shps = get_shps(node)
    lprint('SHAPES', _shps, verbose=verbose)
    if not _shps:
        return None
    if len(_shps) > 1:
        raise ValueError("Multiple shapes found on {} - {}".format(
            node, ', '.join(_shps)))
    return get_single(_shps)


def get_shps(node):
    """Get the shapes on the given node.

    Args:
        node (str): node to read

    Returns:
        (str list): shape nodes
    """
    return cmds.listRelatives(node, shapes=True, noIntermediate=True) or []


def get_val(attr, type_=None, class_=None, verbose=0):
    """Read an attribute value.

    This handles different attribute types without requiring extra flags.
    For example, a string attr will be read as a string.

    Args:
        attr (str): attr to read
        type_ (str): attribute type name (if known)
        class_ (any): cast result to this type
        verbose (int): print process data

    Returns:
        (any): attribute value
    """
    _node, _attr = attr.split('.')
    _type = type_ or cmds.attributeQuery(_attr, node=_node, attributeType=True)
    lprint('TYPE:', _type, verbose=verbose)

    _kwargs = {}
    if _type in ('typed', 'string'):
        _kwargs['asString'] = True
    elif _type in ['float', 'long', 'doubleLinear', 'float3', 'double',
                   'double3', 'time', 'byte', 'bool', 'int', 'doubleAngle',
                   'enum']:
        pass
    elif _type == 'message':
        return get_single(cmds.listConnections(attr, destination=False))
    else:
        raise ValueError('Unhandled type {} on attr {}'.format(_type, attr))

    _result = cmds.getAttr(attr, **_kwargs)
    lprint('RESULT:', _result, verbose=verbose)
    if class_:
        if class_ is qt.HColor:
            _result = class_(*get_single(_result))
        else:
            _result = class_(_result)
    return _result


def get_unique(name, verbose=0):
    """Get unique version of the given node name.

    This is strip any trailing digits from the name provided, and then
    find the first available index which will avoid a name clash.

    Args:
        name (str): node name to check
        verbose (int): print process data

    Returns:
        (str): unique node name
    """
    _clean_name = str(name).split("|")[-1].split(":")[-1]
    _cur_ns = cmds.namespaceInfo(currentNamespace=True).rstrip(":")
    _trg_node = "%s:%s" % (_cur_ns, _clean_name) if _cur_ns else _clean_name
    lprint('NODE EXISTS:', _trg_node, verbose=verbose)

    if cmds.objExists(_trg_node):

        # Strip digits from clean name
        for _ in range(len(_clean_name)):
            if not _clean_name[-1].isdigit():
                break
            _clean_name = _clean_name[: -1]
        _trg_node = "%s:%s" % (_cur_ns, _clean_name)

        if cmds.objExists(_trg_node):

            # Inc digits until unique name
            _idx = 1
            while True:
                _trg_node = "%s:%s%d" % (_cur_ns, _clean_name, _idx)
                if not cmds.objExists(_trg_node):
                    break
                _idx += 1

            _clean_name = "%s%d" % (_clean_name, _idx)

    return _clean_name


def is_visible(node):
    """Test if the given node is visible.

    This tests if the visibiliy attr is turned on for this node and all
    its parents.

    Args:
        node (str): node to test

    Returns:
        (bool): whether node is visible
    """
    _visible = cmds.getAttr(node+'.visibility')
    _parent = get_parent(node)
    if not _parent:
        return _visible
    return _visible and is_visible(_parent)


def load_plugin(plugin, verbose=0):
    """Wrapper for cmds.loadPlugin that doesn't error if plugin is loaded.

    Args:
        plugin (str): name of plugin to load
        verbose (int): print process data
    """
    if not cmds.pluginInfo(plugin, query=True, loaded=True):
        lprint('LOADING PLUGIN', plugin, verbose=verbose)
        cmds.loadPlugin(plugin)
    else:
        lprint('ALREADY LOADED:', plugin, verbose=verbose)


def mel_(cmd, verbose=1):
    """Execute mel and print the code being executed.

    Args:
        cmd (str): mel command to execute
        verbose (int): print process data

    Returns:
        (str): mel result
    """
    lprint(cmd, verbose=verbose)
    return mel.eval(cmd)


def pause_viewports(pause=True):
    """Pause viewports.

    This is a wrapper for the cmds.ogs function which acts as a toggle, which
    can be a bit unpredictable sometimes.

    Args:
        pause (bool): pause state to apply
    """
    _paused = cmds.ogs(query=True, pause=True)
    if pause:
        if _paused:
            print 'VIEWPORTS ALREADY PAUSED'
        else:
            print 'PAUSING VIEWPORTS'
            cmds.ogs(pause=True)
    else:
        if not _paused:
            print 'VIEWPORTS ALREADY UNPAUSED'
        else:
            print 'UNPAUSING VIEWPORTS'
            cmds.ogs(pause=True)


def render(file_, camera=None, layer='defaultRenderLayer', col_mgt=True,
           force=False, verbose=0):
    """Render the current scene.

    Args:
        file_ (str): path to save rendered image
        camera (str): camera to render through
        layer (str): layer to render
        col_mgt (bool): apply colour management
        force (bool): replace existing without confirmation
        verbose (int): print process data
    """
    from maya_psyhive import open_maya as hom
    cmds.loadPlugin('mtoa', quiet=True)
    from mtoa.cmds import arnoldRender

    _cam = camera
    if not _cam:
        _cam = hom.get_active_cam()

    # Prepare output path
    _file = File(get_path(file_))
    _file.test_dir()
    _file.delete(force=force, wording='Replace')

    # Prepare arnold
    cmds.setAttr("defaultArnoldRenderOptions.abortOnError", False)
    cmds.setAttr("defaultArnoldDriver.colorManagement", int(col_mgt))
    cmds.setAttr("defaultArnoldDriver.mergeAOVs", True)
    _extn = {'jpg': 'jpeg'}.get(_file.extn, _file.extn)
    cmds.setAttr('defaultArnoldDriver.aiTranslator', _extn, type='string')
    cmds.setAttr('defaultArnoldDriver.prefix',
                 "{}/{}".format(_file.dir, _file.basename), type='string')
    cmds.setAttr("defaultRenderGlobals.animation", False)

    # Execute renders
    assert not _file.exists()
    arnoldRender.arnoldRender(
        640, 640, True, True, _cam, ' -layer '+layer)
    if not _file.exists():
        _tmp_file = File('{}/{}_1.{}'.format(
            _file.dir, _file.basename, _file.extn))
        print ' - TMP FILE', _tmp_file.path
        assert _tmp_file.exists()
        _tmp_file.move_to(_file)
    assert _file.exists()
    lprint('RENDERED IMAGE', _file.path, verbose=verbose)


def set_col(node, col):
    """Set viewport colour of the given node.

    Args:
        node (str): node to change colour of
        col (str): colour to apply
    """
    if col not in COLS:
        raise ValueError(
            "Col {} not in colour list: {}".format(col, COLS))
    cmds.setAttr(node+'.overrideEnabled', 1)
    cmds.setAttr(node+'.overrideColor', COLS.index(col))


def set_end(frame):
    """Set timeline end frame.

    Args:
        frame (float): end time
    """
    cmds.playbackOptions(maxTime=frame, animationEndTime=frame)


def set_fps(fps):
    """Set current frame rate.

    Args:
        fps (float): fps to apply
    """
    cmds.currentUnit(time={24: 'film', 30: 'ntsc'}[fps])


def set_namespace(namespace, clean=False, verbose=0):
    """Set current namespace, creating it if required.

    Args:
        namespace (str): namespace to apply
        clean (bool): delete all nodes in this namespace
        verbose (int): print process data
    """
    # assert namespace.startswith(':')

    if clean and cmds.namespace(exists=namespace):

        # Remove nodes
        _to_delete = [_node for _node in cmds.ls()
                      if _node.split('->')[-1].startswith(
                          namespace.lstrip(":")+":")]
        if _to_delete:
            lprint('DELETING', _to_delete, verbose=verbose)
            cmds.delete(_to_delete)

        # Remove namespaces
        _sub_nss = cmds.namespaceInfo(namespace, listNamespace=True) or []
        for _ns in reversed(_sub_nss):
            if cmds.objExists(_ns):
                cmds.delete(_ns)
                continue
            cmds.namespace(removeNamespace=':'+_ns)

    if not cmds.namespace(exists=namespace):
        cmds.namespace(addNamespace=namespace)
    cmds.namespace(setNamespace=namespace)


def set_res(res):
    """Set render resolution.

    Args:
        res (tuple): width/height
    """
    _width, _height = res
    cmds.setAttr("defaultResolution.aspectLock", False)
    cmds.setAttr('defaultResolution.width', _width)
    cmds.setAttr('defaultResolution.height', _height)


def set_start(frame):
    """Set timeline start frame.

    Args:
        frame (float): start frame
    """
    cmds.playbackOptions(minTime=frame, animationStartTime=frame),


def set_val(attr, val, verbose=0):
    """Set value of the given attribute.

    This function aims to allow an attribute to be set without having to
    worry about its type, eg. string, float, col attrs.

    Args:
        attr (str): attribute to set
        val (any): value to apply
        verbose (int): print process data
    """
    from maya_psyhive import open_maya as hom

    _args = [val]
    _kwargs = {}
    if isinstance(val, qt.HColor):
        _args = val.to_tuple(mode='float')
    elif isinstance(val, hom.BaseArray3):
        _args = val.to_tuple()
    elif isinstance(val, six.string_types):
        _kwargs['type'] = 'string'
    elif isinstance(val, (list, tuple)):
        _args = val

    lprint('APPLYING VAL', attr, _args, _kwargs, verbose=verbose)
    try:
        cmds.setAttr(attr, *_args, **_kwargs)
    except RuntimeError:
        print 'ARGS/KWARGS', _args, _kwargs
        raise RuntimeError('Failed to setAttr {}'.format(attr))


def use_tmp_ns(func):
    """Decorator which executes function in a temporary namespace.

    Args:
        func (fn): function to execute

    Returns:
        (fn): decorated function
    """
    return get_ns_cleaner(':tmp')(func)
