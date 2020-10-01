"""Tools for checking vendor files remotely.

This tools set is designed to be sent to vendors to allow them to
check their deliveries before sending them to psyop.
"""

from maya import cmds

from psyhive import host, qt, py_gui
from psyhive.tools import ingest
from psyhive.utils import File, get_plural, check_heart, lprint

from maya_psyhive import ref
from maya_psyhive.utils import DEFAULT_NODES

_STEPS = ['model', 'rig', 'shade', 'previz', 'animation', 'lighting']
_GROUPS = ['CHAR', 'PROPS', 'SET', 'CAMERA', 'JUNK']
PYGUI_TITLE = 'Psyop remote ingest tools'


py_gui.set_section('Check', collapse=False)


def _find_scene_name_issues(file_):
    """Find issues with current scene naming.

    Args:
        file_ (File): current scene

    Returns:
        (str list): issues with naming
    """
    _issues = []

    try:
        _tag, _step, _ver = ingest.parse_basename(file_.basename)
    except ValueError:
        _issues.append('Basename fails naming convention: '+file_.basename)
        return _issues

    print ' - TAG/STEP/VER', _tag, _step, _ver
    if _step not in _STEPS:
        _issues.append('Step {} not in: {}'.format(
            _step, ', '.join(_STEPS)))
    elif _step in ['model', 'rig', 'shade']:
        if file_.extn != 'mb':
            _issues.append('File extension for {} should be mb'.format(_step))
    elif _step in ['previz', 'animation', 'lighting']:
        if file_.extn != 'ma':
            _issues.append('File extension for {} should be ma'.format(_step))
    else:
        raise ValueError(_step)

    return _issues


def _find_ref_namespace_issues(ref_):
    """Find any issues with the reference namespace.

    Args:
        ref_ (FileRef): reference to check

    Returns:
        (str list): issues with reference namespace
    """
    _issues = []

    if not ref_.namespace:
        _issues.append("Reference {} has no namespace".format(ref_.ref_node))
        return _issues
    if ref_.namespace.isupper():
        _issues.append(
            "Reference {} has capitalised namespace".format(ref_.namespace))
    if ref_.namespace.count('_') not in (0, 1):
        _issues.append(
            "Reference {} has too many underscores".format(ref_.namespace))
    elif (
            ref_.namespace.count('_') == 1 and
            not ref_.namespace.split('_')[-1].isdigit()):
        _issues.append(
            "Reference {} does not end with a number".format(ref_.namespace))

    return _issues


def _find_ref_top_node_issues(ref_):
    """Find issues with ref top node - eg. bad grouping, no top node.

    Args:
        ref_ (FileRef): ref to check

    Returns:
        (list, bool): issues, junk
    """
    _issues = []
    _junk = False
    _top_node = ref_.find_top_node(catch=True)

    if not _top_node:
        if ref_.find_top_nodes():
            _issues.append(
                "Reference {} has multiple top nodes".format(
                    ref_.namespace))
        else:
            _issues.append(
                "Reference {} has no top node".format(
                    ref_.namespace))

    else:

        # Check parenting
        _parent = _top_node.get_parent()
        if not _parent:
            _issues.append(
                "Reference {} is not in a standard group ({})".format(
                    ref_.namespace, ', '.join(_GROUPS)))
        elif _parent not in _GROUPS:
            _issues.append(
                'Reference {} is in {}, not a standard group ({})'.format(
                    ref_.namespace, _parent, ', '.join(_GROUPS)))

        if _parent == 'JUNK':
            print '   - JUNK'
            _junk = True

    return _issues, _junk


def _find_ref_issues(ref_):
    """Find any issues with the given reference.

    Args:
        ref_ (FileRef): reference to check

    Returns:
        (str list): issues with reference
    """
    _file = File(host.cur_scene())

    _issues = []

    # Check namespace
    _issues += _find_ref_namespace_issues(ref_)
    if not ref_.namespace:
        return _issues

    # Check top node
    _top_node_issues, _junk = _find_ref_top_node_issues(ref_)
    _issues += _top_node_issues
    if _junk:
        return _issues

    # Check ref file path
    _ref_file = File(ref_.path)
    print '   - FILE', _ref_file.path
    _local_file = File('{}/{}'.format(_file.dir, _ref_file.filename))
    if ingest.is_vendor_file(_ref_file):
        _vendor_file = ingest.VendorFile(_ref_file)
        print '   - VENDOR FILE'
        if _vendor_file.step != 'rig':
            _issues.append("Reference {} is not a rig".format(ref_.namespace))
    elif ingest.is_psy_asset(_ref_file):
        _psy_file = ingest.PsyAsset(_ref_file)
        print '   - PSYOP FILE'
        if _psy_file.step != 'rig':
            _issues.append(
                "Psyop reference {} is not a rig".format(ref_.namespace))
    elif not _local_file.exists():
        print '   - OFF-PIPELINE FILE'
        _issues.append(
            "Reference {} has an off-pipline file {} which isn't "
            "provided in the current directory {}".format(
                ref_.namespace, _ref_file.filename, _file.dir))

    return _issues


@py_gui.install_gui(hide=['verbose'])
def check_current_scene(show_dialog=True, verbose=1):
    """Check current scene for ingestion issues.

    Args:
        show_dialog (bool): show status dialog on completion
        verbose (int): print process data

    Returns:
        (str list): list of issues with current file
    """
    _file = File(host.cur_scene())
    _issues = []
    lprint('FILE', _file, verbose=verbose)
    lprint(' - BASENAME', _file.basename, verbose=verbose)

    # Check current scene filename
    _issues += _find_scene_name_issues(_file)

    # Check maya version
    _ver = int(cmds.about(version=True))
    if _ver != 2018:
        _issues.append('Bad maya version {:d}'.format(_ver))

    # Check for unwanted node types
    for _type in ['displayLayer', 'renderLayer']:
        _lyrs = [_lyr for _lyr in cmds.ls(type=_type)
                 if _lyr not in DEFAULT_NODES
                 if not cmds.referenceQuery(_lyr, isNodeReferenced=True)]
        if _lyrs:
            _issues.append('Scene has {} layers: {}'.format(
                _type.replace("Layer", ""), ', '.join(_lyrs)))
    for _type in ['unknown']:
        _nodes = [_node for _node in cmds.ls(type=_type)
                  if _node not in DEFAULT_NODES
                  if not cmds.referenceQuery(_node, isNodeReferenced=True)]
        if _nodes:
            _issues.append('Scene has {} nodes: {}'.format(
                _type, ', '.join(_nodes)))

    # Check references
    _refs = ref.find_refs(unloaded=False)
    lprint('CHECKING {:d} REFS'.format(len(_refs)), verbose=verbose)
    for _ref in _refs:
        lprint(' - CHECKING', _ref, verbose=verbose)
        _issues += _find_ref_issues(_ref)

    # Print summary
    if verbose:
        print '\nSUMMARY: FOUND {:d} ISSUE{}'.format(
            len(_issues), get_plural(_issues).upper())
        for _idx, _issue in enumerate(_issues):
            print ' {:5} {}'.format('[{:d}]'.format(_idx+1), _issue)
        print
    if not show_dialog:
        pass
    elif not _issues:
        qt.notify(
            'No issues found.\n\nFile is read to send to psyop.',
            verbose=0)
    else:
        qt.notify_warning(
            'This file has {:d} issue{}.\n\nCheck the script editor for '
            'details.'.format(len(_issues), get_plural(_issues)),
            verbose=0)

    return _issues


py_gui.set_section('Fix', collapse=False)


def fix_namespaces():
    """Fix namespaces to follow psyop naming."""
    _used = []
    _to_rename = []
    for _ref in ref.find_refs(unloaded=False):
        if not _find_ref_namespace_issues(_ref):
            continue
        _base = _ref.namespace.split('_')[0]
        _name = _base
        _idx = 1
        while not cmds.namespace(exists=_name) and _name in _used:
            check_heart()
            _name = '{}_{:d}'.format(_base, _idx)
            _idx += 1
        print _ref, _name
        _used.append(_name)
        _to_rename.append((_ref, _name))

    if not _to_rename:
        print 'NOTHING TO FIX'
        return
    qt.ok_cancel('Rename {:d} ref{}?'.format(
        len(_to_rename), get_plural(_to_rename)))
    for _ref, _name in qt.progress_bar(_to_rename):
        _ref.rename(_name)


def fix_groups():
    """Fix groups to follow psyop scene organisation."""
    _to_fix = []
    for _ref in ref.find_refs(unloaded=False):
        _top_node = _ref.find_top_node(catch=True)
        if not _top_node:
            continue
        _parent = _top_node.get_parent()
        if _parent in _GROUPS:
            continue
        if '/layout/' in _ref.path:
            _grp = 'JUNK'
        elif '/camera/' in _ref.path:
            _grp = 'CAMERA'
        elif '/prop/' in _ref.path:
            _grp = 'PROPS'
        elif '/character/' in _ref.path:
            _grp = 'CHAR'
        else:
            print 'FAILED', _ref.path
            continue
        print _ref, _parent, _grp
        _to_fix.append((_top_node, _grp))

    if not _to_fix:
        print 'NOTHING TO FIX'
        return
    qt.ok_cancel('Group {:d} ref{}?'.format(
        len(_to_fix), get_plural(_to_fix)))
    for _top_node, _grp in qt.progress_bar(_to_fix):
        _top_node.add_to_grp(_grp)
