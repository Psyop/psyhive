"""Front end tools for ingestion."""

import time

from psyhive import qt
from psyhive.tools import catch_error
from psyhive.utils import get_plural, Dir, abs_path, get_time_t

from .ing_seq import VendorSeq


@catch_error
def ingest_seqs(dir_, vendor):
    """Ingest images sequences from the given directory.

    Args:
        dir_ (str): directory to search
        vendor (str): name of vendor
    """
    assert vendor

    _dir = Dir(abs_path(dir_))
    print 'READING', _dir.path
    print ' - VENDOR', vendor
    _seqs = _dir.find_seqs()
    print ' - FOUND {:d} SEQS\n'.format(len(_seqs))

    _statuses = {}
    _to_ingest = []
    for _seq in qt.progress_bar(_seqs, 'Checking {:d} seq{}'):

        print 'PATH', _seq.path
        _status = None
        _seq = VendorSeq(_seq)
        assert isinstance(_seq, VendorSeq)

        # Get status
        try:
            _out = _seq.to_psy_file_seq()
        except ValueError as _exc:
            _status = _exc.message
        else:
            print ' - OUTPUT', _out.path

            if not _out.exists():
                _status = 'Ready to ingest'
                _to_ingest.append(_seq)
            elif not _out.get_sg_data():
                _status = 'Needs register in sg'
                _to_ingest.append(_seq)
            else:
                _status = 'Already ingested'

        assert _status

        _statuses[_seq] = _status
        print ' - STATUS', _status

        print ' - MTIME', time.strftime('%m/%d/%y', get_time_t(_seq.mtime))
        print

    print

    # Execute ingestion
    if not _to_ingest:
        return
    qt.ok_cancel(
        'Ingest {:d} seq{}?'.format(len(_to_ingest), get_plural(_to_ingest)),
        verbose=0)
    for _idx, _seq in qt.progress_bar(
            enumerate(_to_ingest), 'Ingesting {:d} seq{}',
            stack_key='IngestSeqs'):
        print '({:d}/{:d}) [INGESTING] {}'.format(
            _idx+1, len(_to_ingest), _seq.path)
        _seq.ingest(vendor=vendor)
