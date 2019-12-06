"""Tools for Clash Royale Holdays project."""

import pprint
import collections

from maya import cmds

import six
import tank

from psyhive import qt, py_gui, icons, tk, pipe
from psyhive.tools import hive_bro
from psyhive.utils import get_single, lprint, wrap_fn

from maya_psyhive import ref, tex
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_unique, get_parent

LABEL = "Clash Royale Holidays"
ICON = icons.EMOJI.find('Christmas Tree')
_AI_ATTRS = {
    'aiSubdivType': 'subdiv_type',
    'aiSubdivIterations': 'subdiv_iterations',
    'aiSssSetname': 'set_name',
    'aiOpaque': 'opaque',
}


py_gui.install_gui('Crowd standins')


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


def _get_default_browser_dir():
    """Get default directory for file browser.

    Returns:
        (str): browser dir
    """
    _works = [tk.cur_work()] + hive_bro.get_recent_work()
    _shots = [_work.shot for _work in _works
              if _work and _work.shot] + tk.find_shots()
    _dir = None
    for _shot in _shots:
        _dir = _shot.find_step_root('animation').map_to(
            _shot.output_type_type, output_type='animcache', Task='animation')
        if not _dir.exists():
            continue
        return _dir.path

    return None


def _build_aip_node(shd, standin, meshes, ai_attrs=None, name=None, verbose=0):
    """Build aiSetParameter node.

    Args:
        shd (HFnDependencyNode): shader to apply
        standin (HFnDependencyNode): to set parameter on
        meshes (HFnDependencyNode list): meshes to apply set param to
        ai_attrs (dict): override ai attrs to check
        name (str): override name
        verbose (int): print process data
    """
    _ai_attrs = ai_attrs if ai_attrs is not None else _AI_ATTRS
    print '   - AI ATTRS', _ai_attrs

    # Create standin node
    _aip = hom.CMDS.createNode(
        'aiSetParameter', name='{}_AIP'.format(name or shd.name()))
    _aip.plug('out').connect(_get_next_idx(standin.plug('operators')))
    if shd:
        _aip.plug('assignment[0]').set_val("shader='{}'".format(shd))
    lprint(' - AIP', _aip, verbose=verbose)

    # Determine AIP settings to apply
    _sels = []
    _ai_attr_vals = collections.defaultdict(set)
    for _mesh in meshes:
        for _ai_attr in _ai_attrs:
            _plug = _mesh.plug(_ai_attr)
            _type = 'string' if _plug.get_type() == 'enum' else None
            _val = _plug.get_val(type_=_type)
            lprint(' - READ', _plug, _val, verbose=verbose)
            if not _type:
                _default = _plug.get_default()
                if _default == _val:
                    lprint(' - REJECTED DEFAULT VAL', verbose=verbose)
                    continue
            _ai_attr_vals[_ai_attr].add(_val)

        _tfm = get_parent(_mesh)
        _sels.append('*:{}/*'.format(_tfm.split(":")[-1]))

    # Apply API settings
    _aip.plug('selection').set_val(' or '.join(_sels))
    for _ai_attr, _attr in _ai_attrs.items():
        _vals = sorted(_ai_attr_vals[_ai_attr])
        lprint(' - AI ATTR', _attr, _ai_attr, _vals, verbose=verbose)
        _val = get_single(_vals, catch=True)
        if len(_vals) == 1 and _val not in [None, '']:
            lprint(' - APPLY', _attr, _val, verbose=verbose)
            if isinstance(_val, six.string_types):
                _val = "{}='{}'".format(_attr, _val)
            else:
                _val = "{}={}".format(_attr, _val)
            _get_next_idx(_aip.plug('assignment')).set_val(_val)

    return _aip


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
    _out = tk.get_output(abc)
    if not _out:
        return None

    _shotgun = tank.platform.current_engine().shotgun
    _project = pipe.cur_project()

    if mode == 'abc':
        _sg_data = get_single(_shotgun.find(
            "PublishedFile", filters=[
                ["project", "is", [tk.get_project_data(_project)]],
                ["entity", "is", [tk.get_shot_data(_out.shot)]],
                ["sg_format", "is", 'alembic'],
                ["sg_component_name", "is", _out.output_name],
                ["version_number", "is", _out.version],
            ],
            fields=["code", "name", "sg_status_list", "sg_metadata", "path"]))
        _data = eval(_sg_data['sg_metadata'])
        _result = _data['start_frame'], _data['end_frame']
    elif mode == 'shot':
        _data = get_single(tank.platform.current_engine().shotgun.find(
            'Shot', filters=[
                ["project", "is", [tk.get_project_data(_project)]],
                ["code", "is", [tk.get_shot_data(_out.shot)['name']]]],
            fields=["sg_cut_in", "sg_cut_out"]), catch=True)
        pprint.pprint(_data)
        _result = _data['sg_cut_in'], _data['sg_cut_out'] if _data else None
    else:
        raise ValueError(mode)

    if verbose:
        pprint.pprint(_data)

    return _result


@py_gui.install_gui(
    label='Create aiStandIn from selected shade',
    browser={'archive': py_gui.BrowserLauncher(
        get_default_dir=_get_default_browser_dir, title='Select archive')},
    hide=['verbose'])
def create_standin_from_sel_shade(
        archive=('P:/projects/clashroyale2019_34814P/sequences/'
                 'crowdCycles25Fps/cid00Aid001/animation/output/animcache/'
                 'animation_archer/v014/'
                 'alembic/cid00Aid001_animation_archer_v014.abc'),
        verbose=0):
    """Create aiStandIn from selected shade asset.

    The shader is read from all mesh nodes in the shade asset, and then this
    is used to create an aiSetParameter node on the standin for each shader.
    If all the meshes using the shader has matching values for ai attrs,
    these values are applied as overrides on the aiSetParameter node.

    Args:
        archive (str): path to archive to apply to standin
        verbose (int): print process data
    """
    _shade = ref.get_selected(catch=True)
    if not _shade:
        qt.notify_warning('No shade asset selected.\n\nPlease select a shade '
                          'asset to read shaders from.')
        return

    # Create standin
    _standin = hom.CMDS.createNode('aiStandIn')
    _standin.plug('dso').set_val(archive)
    _standin.plug('useFrameExtension').set_val(True)

    # Read shader assignments
    _shds = collections.defaultdict(list)
    for _mesh in _shade.find_meshes():
        if _mesh.clean_name == 'color_switch_Geo':
            continue
        _shd = tex.read_shd(_mesh)
        if not _shd:
            continue
        _shds[_shd].append(_mesh.shp)

    # Build col switches aip
    _aip = _build_aip_node(
        shd=None, ai_attrs={}, meshes=[], standin=_standin,
        name='{}_colorSwitches'.format(_shade.namespace))
    _aip.plug('selection').set_val('*')
    _geo = _shade.get_node('GEO')
    for _attr in _geo.list_attr(userDefined=True) or []:
        _val = '{}={}'.format(_attr, _geo.plug(_attr).get_val(type_='int'))
        _get_next_idx(_aip.plug('assignment')).set_val(_val)

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

        _build_aip_node(shd=_shd_node, meshes=_meshes, standin=_standin)

    _standin.select()

    # Init updates to happen after abc load
    _rng = _get_abc_range_from_sg(archive)
    _name = get_unique('{}_AIS'.format(_shade.namespace))
    cmds.evalDeferred(
        wrap_fn(_finalise_standin, node=_standin, range_=_rng, name=_name),
        lowestPriority=True)

    print 'CREATED', _standin


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
    print 'FINALISE STANDIN', node
    print ' - RANGE', range_

    # Fix names
    _parent = node.get_parent()
    print ' - RENAMING', name, _parent
    cmds.rename(_parent, name)
    _node = node.rename(name+"Shape")
    _plug = _node.plug('frameNumber')
    if not range_:
        return

    # Clean frame expression
    print ' - PLUG', _plug, _plug.find_driver()
    print ' - BREAKING CONNECTIONS'
    _plug.break_connections()

    # Build expression
    if range_:
        print ' - BUILDING EXPRESSION'
        _str = '\n'.join([
            '{plug} = ((frame - {start}) % ({end} - {start} + 1)) + {start};',
        ]).format(start=range_[0], end=range_[1], plug=_plug)
        lprint(_str, verbose=verbose)
        _expr = cmds.expression(string=_str, timeDependent=True)
        print ' - CREATED EXPRESSION', _expr
