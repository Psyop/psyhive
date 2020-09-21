"""Front end tools for ingestion."""

from psyhive import qt
from psyhive.tools import catch_error
from psyhive.utils import get_plural, Dir, abs_path

from .ing_utils import vendor_from_path
from .ing_vendor_seq import VendorSeq


@catch_error
def ingest_seqs(dir_, vendor, filter_=None, force=False,
                resubmit_transgens=False):
    """Ingest images sequences from the given directory.

    Args:
        dir_ (str): directory to search
        vendor (str): name of vendor
        filter_ (str): apply path filter
        force (bool): ingest without confirmation
        resubmit_transgens (bool): resubmit any submitted transgens
    """
    _dir = Dir(abs_path(dir_))
    print 'READING', _dir.path
    assert _dir.exists()
    _seqs = _dir.find_seqs(filter_=filter_)
    print ' - FOUND {:d} SEQS'.format(len(_seqs))

    # Set vendor
    _vendor = vendor or vendor_from_path(_dir.path)
    assert _vendor
    print ' - VENDOR', _vendor
    print

    # Check images
    _statuses = {}
    _to_ingest = []
    for _idx, _seq in qt.progress_bar(
            enumerate(_seqs), 'Checking {:d} seq{}'):

        print '[{:d}/{:d}] PATH {}'.format(_idx+1, len(_seqs), _seq.path)

        # Check ingestion status
        _status = _ingestable = None
        try:
            _seq = VendorSeq(_seq)
        except ValueError:
            _status, _ingestable = 'Fails naming convention', _seq.basename
        else:
            assert isinstance(_seq, VendorSeq)
            _status, _ingestable = _seq.get_ingest_status(
                resubmit_transgens=resubmit_transgens)
        print ' - STATUS', _status

        assert _status
        assert _ingestable is not None
        if _ingestable:
            _to_ingest.append(_seq)
        _statuses[_seq] = _status

    # Print summary
    print '\nSUMMARY:'
    print '\n'.join([
        '    {} - {:d}'.format(_status, _statuses.values().count(_status))
        for _status in sorted(set(_statuses.values()))])
    print 'FOUND {:d} SEQ{} TO INGEST'.format(
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
