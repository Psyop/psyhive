"""Top level tools for maya ingestion."""

from psyhive import qt, host
from psyhive.tools.ingest import vendor_from_path
from psyhive.utils import Dir, abs_path, File, get_plural

from .ming_vendor_scene import VendorScene


def _get_ingestable_scenes(dir_, filter_):
    """Find scenes ready for ingestion.

    Args:
        dir_ (str): directory to search for scenes
        filter_ (str): filter_ file list

    Returns:
        (VendorScene list, dict): list of ingestible scenes, scene statuses
    """

    # Find scenes
    _dir = Dir(abs_path(dir_))
    print 'READING', _dir.path
    assert _dir.exists()
    _scenes = [
        _file for _file in _dir.find(type_='f', class_=File, filter_=filter_)
        if _file.extn in ('ma', 'mb')]
    print ' - FOUND {:d} SCENES'.format(len(_scenes))

    # Check scenes
    _statuses = {}
    _to_ingest = []
    for _idx, _scene in qt.progress_bar(
            enumerate(_scenes), 'Checking {:d} scene{}'):

        print '[{:d}/{:d}] PATH {}'.format(_idx+1, len(_scenes), _scene.path)

        # Check ingestion status
        _status = _ingestable = None
        try:
            _scene = VendorScene(_scene)
        except ValueError:
            print ' - FAILS NAMING CONVENTION'
            _status, _ingestable = 'Fails naming convention', False
        else:
            _status, _ingestable = _scene.get_ingest_status()
        print ' - STATUS', _status
        # print ' - CAM', _scene.scene_get_cam()

        assert _status
        assert _ingestable is not None

        if _ingestable:
            assert isinstance(_scene, VendorScene)
            _to_ingest.append(_scene)
        _statuses[_scene] = _status

    print '\nALREADY INGESTED: {}\n'.format(
        sorted(set([
            _scene.to_psy_work().get_shot().name
            for _scene, _status in _statuses.items()
            if _status == 'Already ingested'])))

    # Print summary
    print '\n\n[SUMMARY]'
    print '\n'.join([
        '    {} - {:d}'.format(_status, _statuses.values().count(_status))
        for _status in sorted(set(_statuses.values()))])
    print '\nFOUND {:d} SCENE{} TO INGEST'.format(
        len(_to_ingest), get_plural(_to_ingest).upper())

    return _to_ingest, _statuses


def ingest_vendor_anim(
        dir_, vendor=None, force=False, filter_=None, ignore_extn=False,
        ignore_dlayers=False, ignore_rlayers=False,
        ignore_multi_top_nodes=False):
    """Ingest vendor animation files.

    Args:
        dir_ (str): vendor in folder
        vendor (str): vendor name
        force (bool): lose current scene changes without confirmation
        filter_ (str): filter file list
        ignore_extn (bool): ignore file extension issues
        ignore_dlayers (bool): ignore display layer issues
        ignore_rlayers (bool): ignore render layer issues
        ignore_multi_top_nodes (bool): ignore multiple top node issues
    """

    # Set vendor
    _vendor = vendor or vendor_from_path(dir_)
    assert _vendor
    print ' - VENDOR', _vendor
    print

    # Read ingestible scenes
    _to_ingest, _statuses = _get_ingestable_scenes(dir_=dir_, filter_=filter_)
    if not _to_ingest:
        return
    if not force:
        qt.ok_cancel(
            'Ingest {:d} scene{}?'.format(
                len(_to_ingest), get_plural(_to_ingest)),
            verbose=0)
        print 'HANDLE UNSAVED CHANGES'
        host.handle_unsaved_changes()
        print 'HANDLED UNSAVED CHANGES'

    # Ingest scenes
    _issues = []
    _ingest_kwargs = dict(
        ignore_extn=ignore_extn,
        ignore_dlayers=ignore_dlayers,
        ignore_multi_top_nodes=ignore_multi_top_nodes,
        ignore_rlayers=ignore_rlayers)
    for _idx, _scene in qt.progress_bar(
            enumerate(_to_ingest), 'Ingesting {:d} scene{}'):

        print '[{:d}/{:d}] PATH {}'.format(
            _idx+1, len(_to_ingest), _scene.path)

        _scene.check_workspaces()

        # Check ingestion status
        assert isinstance(_scene, VendorScene)
        _scene_isses = _scene.get_ingest_issues(**_ingest_kwargs)
        if _scene_isses:
            _issues.append((_scene, _scene_isses))
        print ' - CAM', _scene.scene_get_cam()

        _scene.ingest(vendor=vendor, force=True)
        _status, _ = _scene.get_ingest_status(**_ingest_kwargs)
        _statuses[_scene] = _status

    if _issues:
        print '\n\n[INGESTION ISSUES]\n'
        for _scene, _scene_issues in _issues:
            print 'SCENE', _scene.path
            for _issue in _scene_issues:
                print ' -', _issue

    # Print summary
    print '\n\n[SUMMARY]'
    print '\n'.join([
        '    {} - {:d}'.format(_status, _statuses.values().count(_status))
        for _status in sorted(set(_statuses.values()))])
    print '\nFOUND {:d} SCENE{} TO INGEST'.format(
        len(_to_ingest), get_plural(_to_ingest).upper())

