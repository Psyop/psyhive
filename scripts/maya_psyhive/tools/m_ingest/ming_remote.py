"""Tools for checking vendor files remotely.

This tools set is designed to be sent to vendors to allow them to
check their deliveries before sending them to psyop.
"""

from maya import cmds

from psyhive import host, qt
from psyhive.tools import ingest
from psyhive.utils import File, get_plural

from maya_psyhive import ref
from maya_psyhive.utils import DEFAULT_NODES

_STEPS = ['model', 'rig', 'shade', 'animation', 'lighting']
_GROUPS = ['CHAR', 'PROPS', 'SET', 'CAMERA', 'JUNK']


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
    elif _step in ['model', 'rig', 'shade'] and file_.extn != 'mb':
        _issues.append('File extension for {} should be mb'.format(_step))
    elif _step in ['animation', 'lighting'] and file_.extn != 'ma':
        _issues.append('File extension for {} should be ma'.format(_step))
    else:
        raise ValueError

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
    _top_node = ref_.find_top_node(catch=True)
    if not _top_node:
        _issues.append("Reference {} has no top node".format(ref_.namespace))
        return _issues

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


def check_current_scene(show_dialog=True):
    """Check current scene for ingestion issues.

    Args:
        show_dialog (bool): show status dialog on completion

    Returns:
        (str list): list of issues with current file
    """
    _file = File(host.cur_scene())
    _issues = []
    print 'FILE', _file
    print ' - BASENAME', _file.basename

    # Check current scene filename
    _issues += _find_scene_name_issues(_file)

    # Check maya version
    _ver = int(cmds.about(version=True))
    if _ver != 2018:
        _issues.append('Bad maya version {:d}'.format(_ver))

    # Check for unwanted layers
    for _type in ['displayLayer', 'renderLayer']:
        _lyrs = [_lyr for _lyr in cmds.ls(type=_type)
                 if _lyr not in DEFAULT_NODES]
        if _lyrs:
            _issues.append('Scene has {} layers: {}'.format(
                _type.replace("Layer", ""), ', '.join(_lyrs)))

    # Check references
    _refs = ref.find_refs()
    print 'CHECKING {:d} REFS'.format(len(_refs))
    for _ref in _refs:
        print ' - CHECKING', _ref
        _issues += _find_ref_issues(_ref)

    # Print summary
    print '\nSUMMARY: FOUND {:d} ISSUES'.format(len(_issues))
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
