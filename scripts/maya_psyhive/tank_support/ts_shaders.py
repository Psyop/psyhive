"""Tools for managing aiStandIn outputs."""

import collections
import functools
import pprint
import tempfile

from pymel import core as pm
from maya import cmds

import six
import tank

from psyhive import qt, py_gui, tk2, pipe, host
from psyhive.utils import (
    get_single, lprint, wrap_fn, abs_path, dprint, write_yaml)

from maya_psyhive import tex
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_unique, get_parent, DEFAULT_NODES

_AI_ATTRS = {
    'aiSubdivType': 'subdiv_type',
    'aiSubdivIterations': 'subdiv_iterations',
    'aiSssSetname': 'set_name',
    'aiOpaque': 'opaque',
}


py_gui.install_gui('Crowd standins')


def _user_attr_sort(attr):
    """Sorting for shade GEO node user attr overrides.

    Args:
        attr (str): attribute name

    Returns:
        (str): sort key
    """
    _order = ['colorSwitch', 'paint', 'paintPattern', 'burnt']
    _idx = _order.index(attr) if attr in _order else len(_order)
    return '{:04d}{}'.format(_idx, attr)


def _get_next_idx(plug, connected=True, value=True, limit=1000, verbose=0):
    """Get next avaliable index for mult indexed attributes.

    In this case there seems to be a strange bug where if the attribute
    is queried then maya/arnold fills it with a weird unicode value. This
    value is idenfied by trying to convert to str in which cases it raises
    a RuntimeError, identifying that attr as available.

    Args:
        plug (HPlug): plug to read
        connected (bool): check for connected attributes
        value (bool): check for attributes with values assigned
        limit (int): number of attrs to search
        verbose (int): print process data

    Returns:
        (HPlug): next free index
    """
    _plug = None
    for _idx in range(limit):

        _plug = hom.HPlug('{}[{:d}]'.format(plug, _idx))
        lprint('TESTING', _plug, verbose=verbose)

        # Test for connection
        if connected and _plug.list_connections(destination=False):
            lprint(' - USED BY CONNECTION', verbose=verbose)
            continue

        # Test for assigned value
        if value:
            try:
                _val = str(_plug.get_attr())
            except (UnicodeEncodeError, RuntimeError):
                pass
            else:
                lprint(' - HAS NON-UNICODE VAL ASSIGNED', _val,
                       verbose=verbose)
                continue

        lprint(' - NO CONNECTION OR VAL', verbose=verbose)
        return _plug

    raise ValueError


def _build_aip_node(shd, merge, meshes, ai_attrs=None, name=None, verbose=0):
    """Build aiSetParameter node.

    Args:
        shd (HFnDependencyNode): shader to apply
        merge (HFnDependencyNode): merge node to connect output to
        meshes (HFnDependencyNode list): meshes to apply set param to
        ai_attrs (dict): override ai attrs to check
        name (str): override name
        verbose (int): print process data
    """
    dprint('BUILD AIP', shd, meshes, verbose=verbose)
    _ai_attrs = ai_attrs if ai_attrs is not None else _AI_ATTRS
    lprint(' - AI ATTRS', _ai_attrs, verbose=verbose)

    # Create standin node
    _aip = hom.CMDS.createNode(
        'aiSetParameter', name='{}_AIP'.format(name or shd.name()))
    _aip.plug('out').connect(_get_next_idx(merge.plug('inputs')))
    if shd:
        _aip.plug('assignment[0]').set_val("shader = '{}'".format(shd))
    lprint(' - AIP', _aip, verbose=verbose)

    # Determine AIP settings to apply
    _sels = []
    _ai_attr_vals = collections.defaultdict(set)
    for _mesh in meshes:
        for _ai_attr in _ai_attrs:
            _plug = _mesh.plug(_ai_attr)
            _type = 'string' if _plug.get_type() == 'enum' else None
            _val = _plug.get_val(type_=_type)
            lprint('   - READ', _plug, _val, verbose=verbose > 1)
            if not _type:
                _default = _plug.get_default()
                if _default == _val:
                    lprint('   - REJECTED DEFAULT VAL', verbose=verbose > 1)
                    continue
            _ai_attr_vals[_ai_attr].add(_val)

        lprint(' - MESH', _mesh, _mesh.namespace, verbose=verbose)
        _prefix = '*:' if _mesh.namespace else '*/'
        _tfm = hom.HFnTransform(get_parent(_mesh))
        _sels.append('{}{}/*'.format(_prefix, _tfm.clean_name))

    # Apply API settings
    _aip.plug('selection').set_val(' or '.join(_sels))
    for _ai_attr, _attr in _ai_attrs.items():
        _vals = sorted(_ai_attr_vals[_ai_attr])
        lprint(' - AI ATTR', _attr, _ai_attr, _vals, verbose=verbose > 1)
        _val = get_single(_vals, catch=True)
        if len(_vals) == 1 and _val not in [None, '']:
            lprint(' - APPLY', _attr, _val, verbose=verbose > 1)
            if isinstance(_val, six.string_types):
                _val = "{} = '{}'".format(_attr, _val)
            else:
                _val = "{} = {}".format(_attr, _val)
            _get_next_idx(_aip.plug('assignment')).set_val(_val)

    # Read displacement
    if shd:
        _add_displacement_override(shd=shd, aip=_aip)

    return _aip


def _add_displacement_override(shd, aip, verbose=0):
    """Add displacement override if applicable.

    Args:
        shd (HFnDepedencyNode): shader node
        aip (HFnDepedencyNode): aiSetParameter node
        verbose (int): print process data
    """
    _shd = tex.find_shd(str(shd), catch=True)
    if not _shd:
        return
    lprint(' - SHD', _shd, verbose=verbose)
    if not _shd.get_se():
        return

    lprint(' - SE', _shd.get_se(), verbose=verbose)
    _displ = get_single(
        _shd.get_se().plug('displacementShader').list_connections(),
        catch=True)
    if not _displ:
        return

    lprint(' - DISPL', _displ, verbose=verbose)
    _val = "disp_map = '{}'".format(_displ)
    _get_next_idx(aip.plug('assignment')).set_val(_val)


def _get_abc_range_from_sg(abc, mode='shot', verbose=0):
    """Read abc frame range from shotgun.

    Args:
        abc (str): path to abc file
        mode (str): where to get range from
            abc - read bake range of abc
            shot - read cut in/out range of shot
        verbose (int): print process data

    Returns:
        (tuple|None): frame range (if any)
    """
    _out = tk2.get_output(abc)
    if not _out:
        lprint('NO OUTPUT', abc, verbose=verbose)
        return None

    _shotgun = tank.platform.current_engine().shotgun
    _project = pipe.cur_project()

    if mode == 'abc':
        _sg_data = get_single(_shotgun.find(
            "PublishedFile", filters=[
                ["project", "is", [tk2.get_project_sg_data(_project)]],
                ["entity", "is", [tk2.get_shot_sg_data(_out.shot)]],
                ["sg_format", "is", 'alembic'],
                ["sg_component_name", "is", _out.output_name],
                ["version_number", "is", _out.version],
            ],
            fields=["code", "name", "sg_status_list", "sg_metadata", "path"]))
        _data = eval(_sg_data['sg_metadata'])
        _result = _data['start_frame'], _data['end_frame']
    elif mode == 'shot':
        _shot = tk2.get_shot(_out.path)
        if not _shot:
            return None
        _data = get_single(tank.platform.current_engine().shotgun.find(
            'Shot', filters=[
                ["project", "is", [tk2.get_project_sg_data(_project)]],
                ["code", "is", [_shot.get_sg_data()['name']]]],
            fields=["sg_cut_in", "sg_cut_out"]), catch=True)
        if verbose:
            print 'SHOT DATA', _shot.get_sg_data()
        if (
                _data and
                _data.get('sg_cut_in') is not None and
                _data.get('sg_cut_out') is not None):
            _result = _data['sg_cut_in'], _data['sg_cut_out']
        else:
            _result = None
    else:
        raise ValueError(mode)

    if verbose:
        pprint.pprint(_data)

    return _result


def _build_col_switches_aip(shade, merge, name):
    """Build col switches override node.

    Args:
        shade (FileRef): shade reference
        merge (HFnDependencyNode): merge node to connect output to
        name (str): base name for nodes (eg. shade namespace)
    """
    _aip = _build_aip_node(
        shd=None, ai_attrs={}, meshes=[], merge=merge,
        name='{}_colorSwitches'.format(name))
    _aip.plug('selection').set_val('*')

    # Add override for user defined attrs on shade GEO node
    _geo = shade.get_node('GEO')
    _attrs = _geo.list_attr(userDefined=True) or []
    _attrs.sort(key=_user_attr_sort)
    for _attr in _attrs:
        _plug = _geo.plug(_attr)
        _type = _plug.get_type()
        _type = {'enum': 'int'}.get(_type, _type)
        _val = '{} {} = {}'.format(
            _type, _attr, _plug.get_val(type_='int'))
        _get_next_idx(_aip.plug('assignment')).set_val(_val)

    print ' - BUILT COL SWITCHES AIP', _aip


def _build_shader_overrides(shade, merge, verbose=0):
    """Build shader overrides.

    Each shader has an aiSetParameter node which applies overrides
    for the geometry in the abc which that shader is applied to.

    Args:
        shade (FileRef): shade reference
        merge (HFnDependencyNode): merge node to connect output to
        verbose (int): print process data
    """
    _shds = collections.defaultdict(list)

    # Read shader assignments
    for _mesh in shade.find_meshes():
        if _mesh.clean_name == 'color_switch_Geo':
            continue
        _shd = tex.read_shd(_mesh, allow_base=True)
        if not _shd:
            continue
        _shds[_shd].append(_mesh.shp)

    # Set up AIP node for each shader
    for _shd in qt.progress_bar(sorted(_shds), 'Applying {:d} shader{}'):

        _meshes = _shds[_shd]
        lprint(' - SHD', _shd, _meshes, verbose=verbose)

        # Read SE + arnold shader
        lprint('   - SE', _shd.get_se(), verbose=verbose)
        _ai_shd = get_single(
            _shd.get_se().plug('aiSurfaceShader').list_connections(),
            catch=True)
        if _ai_shd:
            _ai_shd = hom.HFnDependencyNode(_ai_shd)
        lprint('   - AI SHD', _ai_shd, verbose=verbose)
        _shd_node = _ai_shd or _shd.shd

        _build_aip_node(shd=_shd_node, meshes=_meshes, merge=merge)


def _finalise_standin(node, name, range_, verbose=0):
    """Finalise new aiStandIn node.

    Executes updates to be run after abc has loaded (abc loads using deferred
    evaluation). This includes renaming the transform/shape - if they are
    renamed before abc load the auto generated abc frame expression errors.
    Also the frame expression is regenenerated to make the abc loop - if this
    is generated before abc load then the auto generated expression also
    errors.

    Args:
        node (HFnDependencyNode): aiStandIn node (shape)
        name (str): intended node name (of transform)
        range_ (tuple|None): range to loop (if any)
        verbose (int): print process data
    """
    dprint('FINALISE STANDIN', node, verbose=verbose)
    lprint(' - RANGE', range_, verbose=verbose)

    # Fix names
    _parent = node.get_parent()
    lprint(' - RENAMING', name, _parent, verbose=verbose)
    _parent = cmds.rename(_parent, name)
    lprint(' - PARENT', _parent, verbose=verbose)
    _node = node.rename(name+"Shape")
    _plug = _node.plug('frameNumber')

    # Apply range expression
    if range_:

        # Clean frame expression
        lprint(' - PLUG', _plug, _plug.find_driver(), verbose=verbose)
        lprint(' - BREAKING CONNECTIONS', verbose=verbose)
        _plug.break_connections()

        # Build expression
        if range_:
            lprint(' - BUILDING EXPRESSION', verbose=verbose)
            _str = (
                '{plug} = ((frame - {start}) % ({end} - {start} + 1)) + '
                '{start};').format(start=range_[0], end=range_[1], plug=_plug)
            lprint(_str, verbose=verbose)
            _expr = cmds.expression(string=_str, timeDependent=True)
            lprint(' - CREATED EXPRESSION', _expr, verbose=verbose)

    return hom.HFnTransform(_parent)


def _revert_scene(func):
    """Decorator to save a scene to tmp and then revert it on fn complete.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _revert_scene_fn(*args, **kwargs):
        _cur_file = host.cur_scene()
        _tmp_file = abs_path('{}/_psyhive_tmp.mb'.format(
            tempfile.gettempdir()))
        host.save_as(_tmp_file, force=True)
        _result = func(*args, **kwargs)
        host.open_scene(_tmp_file, force=True)
        if _cur_file:
            cmds.file(rename=_cur_file)
        return _result

    return _revert_scene_fn


class _ShadeScene(object):
    """Represents the shade scene.

    This allow nodes in the current scene to act like nodes in a
    referenced shade asset.
    """

    def get_node(self, name):
        """Get a node matching the given name.

        Args:
            name (str): node name

        Returns:
            (HFnDependencyNode): node
        """
        return hom.HFnDependencyNode(name)

    def find_meshes(self):
        """Find meshes in the current scene.

        Returns:
            (HFnMesh list): meshes
        """
        _meshes = []
        for _shp in hom.CMDS.ls(type='mesh'):
            if _shp.namespace:
                continue
            if _shp.plug('intermediateObject').get_val():
                continue
            _mesh = hom.HFnMesh(get_parent(_shp))
            _meshes.append(_mesh)
        return _meshes


def build_aistandin_from_shade(
        archive, shade=None, animated=True, name=None, deferred=True,
        verbose=0):
    """Create aiStandIn from selected shade asset.

    The shader is read from all mesh nodes in the shade asset, and then this
    is used to create an aiSetParameter node on the standin for each shader.
    If all the meshes using the shader has matching values for ai attrs,
    these values are applied as overrides on the aiSetParameter node.

    Args:
        archive (str): path to archive to apply to standin
        shade (FileRef): shade asset to build overrides from
        animated (bool): whether this archive is animated
        name (str): base name for nodes (normally shade namespace)
        deferred (bool): apply deferrred changes - this allows the
            standin to be generated with no error message as maya
            makes deferred callbacks on aiStandIn create; however
            this cannot be used if running code as part of a publish
        verbose (int): print process data

    Returns:
        (HFnTransform) standin transform
    """
    _name = name or shade.namespace

    # Create standin
    _standin = hom.CMDS.createNode('aiStandIn')
    _standin.plug('dso').set_val(archive)
    _standin.plug('useFrameExtension').set_val(animated)

    _merge = hom.CMDS.createNode(
        'aiMerge', name='{}_mergeOperators'.format(_name))
    _merge.plug('out').connect(_standin.plug('operators[0]'))

    _build_col_switches_aip(
        shade=shade, merge=_merge, name=_name)
    _build_shader_overrides(shade=shade, merge=_merge, verbose=verbose)

    # Init updates to happen after abc load
    _standin.select()
    _rng = _get_abc_range_from_sg(archive) if animated else None
    _ais_name = get_unique(name or '{}_AIS'.format(shade.namespace))
    _finalise_fn = wrap_fn(
        _finalise_standin, node=_standin, range_=_rng, name=_ais_name)
    if deferred:
        cmds.evalDeferred(_finalise_fn, lowestPriority=True)
        _parent = None
    else:
        _parent = _finalise_fn()
        print 'NOT DEFERRED', _parent

    print 'CREATED', _standin, _parent

    return _parent


@_revert_scene
def build_shader_outputs(output, force=True, verbose=1):
    """Build shader outputs for the given shade asset.

    This consists of:

        - mb file containing just shaders for this asset
        - yml file containing list of shaders
        - standin file containing shaders attached to aiStandIn node

    Args:
        output (str): path to aiStandIn output
        force (bool): overrwrite existing files without confirmation
        verbose (int): print process data

    Returns:
        (str): path to output file
    """
    lprint('BUILD aiStandIn MA', output, verbose=verbose)

    # Get paths for standin + rest cache + shade
    _out = tk2.TTOutput(output)
    _shaders = _out.map_to(
        tk2.TTOutputFile, format='shaders', extension='mb')
    _yml = _out.map_to(
        tk2.TTOutputFile, format='shaders', extension='yml')
    _standin = _out.map_to(
        tk2.TTOutputFile, format='aistandin', extension='ma')
    _ver = tk2.TTOutputVersion(output)
    _rest_cache = get_single(_ver.find(
        extn='abc', filter_='restCache'), catch=True)
    if not _rest_cache:
        raise RuntimeError('Missing rest cache '+_ver.path)
    _shade = _ver.find_file(extn='mb', format_='maya')
    lprint(' - VER       ', _ver.path, verbose=verbose)
    lprint(' - SHADE     ', _shade.path, verbose=verbose)
    lprint(' - REST CACHE', _rest_cache, verbose=verbose)
    lprint(' - STANDIN   ', _standin.path, verbose=verbose)
    lprint(' - SHADERS   ', _shaders.path, verbose=verbose)
    assert not _shade == _out.path

    # Build aiStandIn node
    lprint(' - OPENING SHADE SCENE', verbose=verbose)
    host.open_scene(_shade.path, force=True)
    build_aistandin_from_shade(
        archive=_rest_cache, shade=_ShadeScene(), animated=False, name='AIS',
        deferred=False)

    # Remove + save aistandin
    cmds.delete('GEO')
    host.save_as(file_=_standin.path, force=force)

    # Remove standin + save shaders
    cmds.delete('AIS')
    _ses = [str(_se) for _se in cmds.ls(type='shadingEngine')
            if _se not in DEFAULT_NODES]
    lprint(" - SHADING ENGINES", _ses, verbose=verbose)
    host.save_as(_shaders.path, force=force)
    write_yaml(file_=_yml.path, data=_ses)

    return _standin.path


def apply_abc_to_shade_aistandin(namespace, abc):
    """Update shade aiStandIn to match given abc.

    Args:
        namespace (str): shade aiStandIn namespace
        abc (str): path to abc to apply
    """
    _standin = namespace+':AIS'
    pm.setAttr(_standin+'.dso', abc)
    pm.setAttr(_standin+'.useFrameExtension', True)

    _ref = cmds.referenceQuery(_standin, referenceNode=True)
    for _node in cmds.referenceQuery(_ref, nodes=True):

        if not cmds.objectType(_node) == 'aiSetParameter':
            continue

        # Update shader
        _shd_str = cmds.getAttr(_node+'.assignment[0]')
        if _shd_str.startswith('shader = '):
            _cur_shd = _shd_str.split("'")[-2]
            _new_shd = '{}:{}'.format(namespace, _cur_shd.split(':')[-1])
            pm.setAttr(_node+'.assignment[0]',
                       _shd_str.replace(_cur_shd, _new_shd))

        # Update internal reference to allow namespace (rest cache has no
        # namespace but anim caches do)
        _sel_str = cmds.getAttr(_node+'.selection')
        pm.setAttr(_node+'.selection', _sel_str.replace("*/", "*:"))
