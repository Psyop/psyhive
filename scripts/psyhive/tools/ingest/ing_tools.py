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
    _seqs = _dir.find_seqs()
    print 'FOUND {:d} SEQS\n'.format(len(_seqs))

    _statuses = {}
    _to_ingest = []
    for _seq in _seqs:

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

    _f_just = max([len(_seq.filename) for _seq in _statuses])
    _s_just = max([len(_status) for _seq in _statuses.values()])
    for _seq in _statuses:
        # dev.inspect(_seq)
        print ' - '.join([
            _seq.filename.ljust(_f_just),
            _statuses[_seq].ljust(_s_just),
            _seq.path])

    if not _to_ingest:
        return
    qt.ok_cancel('Ingest {:d} seq{}?'.format(
        len(_to_ingest), get_plural(_to_ingest)))
    for _seq in qt.progress_bar(_to_ingest):
        print _seq
        _seq.ingest(vendor=vendor)
