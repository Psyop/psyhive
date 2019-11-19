"""Tools for Clash Royale Holdays project."""

import collections

from maya import cmds

import six

from psyhive import qt, py_gui, icons, tk
from psyhive.tools import hive_bro
from psyhive.utils import get_single, lprint, wrap_fn

from maya_psyhive import ref, tex
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent, get_unique

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


def _build_aip_node(shd, standin, meshes, verbose=0):
    """Build aiSetParameter node.

    Args:
        shd (HFnDependencyNode): shader to apply
        standin (HFnDependencyNode): to set parameter on
        meshes (HFnDependencyNode list): meshes to apply set param to
        verbose (int): print process data
    """
    _aip = hom.CMDS.createNode(
        'aiSetParameter', name='{}_AIP'.format(shd.name()))
    _aip.plug('assignment[0]').set_val("shader='{}'".format(shd))
    _aip.plug('out').connect(_get_next_idx(standin.plug('operators')))
    lprint(' - AIP', _aip, verbose=verbose)

    # Determine AIP settings to apply
    _sels = []
    _ai_attr_vals = collections.defaultdict(set)
    for _mesh in meshes:
        for _ai_attr in _AI_ATTRS:
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
        _sels.append('/{}/{}'.format(get_parent(_mesh), _mesh))

    # Apply API settings
    _aip.plug('selection').set_val(' or '.join(_sels))
    for _ai_attr, _attr in _AI_ATTRS.items():
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
    for _mesh in _shade.find_nodes(type_='mesh'):
        if cmds.getAttr(_mesh+'.intermediateObject'):
            continue
        _shd = tex.read_shd(_mesh)
        print _mesh, _shd
        _shds[_shd].append(_mesh)
    print

    # Set up AIP node for each shader
    for _shd in qt.progress_bar(sorted(_shds), 'Applying {:d} shader{}'):

        print 'SHD', _shd
        _meshes = _shds[_shd]
        lprint('    '+'\n    '.join([str(_mesh) for _mesh in _meshes]),
               verbose=verbose)

        # Read SE + arnold shader
        lprint(' - SE', _shd.get_se(), verbose=verbose)
        _ai_shd = get_single(
            _shd.get_se().plug('aiSurfaceShader').list_connections(),
            catch=True)
        if _ai_shd:
            _ai_shd = hom.HFnDependencyNode(_ai_shd)
        lprint(' - AI SHD', _ai_shd, verbose=verbose)
        _shd_node = _ai_shd or _shd.shd

        _build_aip_node(shd=_shd_node, meshes=_meshes, standin=_standin)

    # Rename avoiding error on frame expression node
    _standin.select()
    _rename = wrap_fn(cmds.rename, get_parent(_standin),
                      get_unique('{}_AIS'.format(_shade.namespace)))
    cmds.evalDeferred(_rename)
