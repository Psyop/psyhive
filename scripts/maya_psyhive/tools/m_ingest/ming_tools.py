"""Top level tools for maya ingestion."""

from psyhive import qt
from psyhive.tools.ingest import vendor_from_path
from psyhive.utils import Dir, abs_path, File, get_plural

from .ming_vendor_scene import VendorScene


def ingest_vendor_anim(dir_, vendor=None, force=False, filter_=None):
    """Ingest vendor animation files.

    Args:
        dir_ (str): vendor in folder
        vendor (str): vendor name
        force (bool): lose current scene changes without confirmation
        filter_ (str): filter file list
    """
    _dir = Dir(abs_path(dir_))
    print 'READING', _dir.path
    assert _dir.exists()
    _scenes = [
        _file for _file in _dir.find(type_='f', class_=File, filter_=filter_)
        if _file.extn in ('ma', 'mb')]
    print ' - FOUND {:d} SCENES'.format(len(_scenes))

    # Set vendor
    _vendor = vendor or vendor_from_path(_dir.path)
    assert _vendor
    print ' - VENDOR', _vendor
    print

    # Check images
    _statuses = {}
    _to_ingest = []
    _issues = []
    for _idx, _scene in qt.progress_bar(
            enumerate(_scenes), 'Checking {:d} scene{}'):

        print '[{:d}/{:d}] PATH {}'.format(_idx+1, len(_scenes), _scene.path)

        # Check ingestion status
        _status = _ingestable = None
        try:
            _scene = VendorScene(_scene)
        except ValueError:
            _status, _ingestable = 'Fails naming convention', _scene.basename
            continue
        else:
            assert isinstance(_scene, VendorScene)
            _status, _ingestable = _scene.get_ingest_status()
        print ' - STATUS', _status
        print ' - CAM', _scene.scene_get_cam()
        if _status == 'Ingestion issues':
            _issues.append(_scene)

        assert _status
        assert _ingestable is not None
        if _ingestable:
            _to_ingest.append(_scene)
        _statuses[_scene] = _status

    if _issues:
        print '\nINGESTION ISSUES:'
        for _scene in _issues:
            print 'SCENE', _scene.path
            for _issue in _scene.scene_get_ingest_issues():
                print ' -', _issue
        print

    # Print summary
    print '\nSUMMARY:'
    print '\n'.join([
        '    {} - {:d}'.format(_status, _statuses.values().count(_status))
        for _status in sorted(set(_statuses.values()))])
    print '\nFOUND {:d} SCENE{} TO INGEST'.format(
        len(_to_ingest), get_plural(_to_ingest).upper())

    # Show different source warning
    _diff_src = [
        _ for _, _status in _statuses.items()
        if _status == 'Already ingested from a different source']
    if _diff_src:
        qt.notify_warning(
            '{:d} of the sequences could not be ingested because they have '
            'already been ingested from a different delivery. This happens '
            'when a vendor provides an update without versioning up.\n\n'
            'See the terminal for details.'.format(len(_diff_src)))

    # Execute ingestion
    if not _to_ingest:
        return
    if not force:
        qt.ok_cancel(
            'Ingest {:d} seq{}?'.format(
                len(_to_ingest), get_plural(_to_ingest)),
            verbose=0)
    for _idx, _seq in qt.progress_bar(
            enumerate(_to_ingest), 'Ingesting {:d} seq{}',
            stack_key='IngestSeqs'):
        print '({:d}/{:d}) [INGESTING] {}'.format(
            _idx+1, len(_to_ingest), _seq.path)
        _seq.ingest(vendor=vendor)
