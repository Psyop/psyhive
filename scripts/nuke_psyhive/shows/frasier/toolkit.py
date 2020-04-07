"""Toolkit for frasier."""

import os
import time
import pprint

import nuke

from psyhive import icons, host
from psyhive.utils import find, File, abs_path, lprint

_DIR = abs_path(os.path.dirname(__file__))
ICON = icons.EMOJI.find("Radioactive")

_REVIEW_DIR = abs_path(
    r'P:\projects\frasier_38732V\production\processed_for_review')
_REVIEW_MOV_EXPORT_NK = '{}/review_mov_export.nk'.format(_DIR)


class _InputReviewMov(File):
    """Mov file to be comped into grid."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to mov file
        """
        super(_InputReviewMov, self).__init__(file_)
        _tokens = self.basename.split('_')
        if 'V' in _tokens[-1]:
            self.tag, _ver = _tokens[-1].split("V")
            self.version = int(_ver)
        else:
            self.tag = _tokens[-1]
            self.version = None
        self.review_mov = _OutputReviewMov(abs_path('{}/{}{}.mov'.format(
            _REVIEW_DIR, '_'.join(_tokens[:-1]),
            '_v{:03}'.format(self.version) if self.version else '')))
        if self.tag.lower() not in [
                'producer', 'front', 'frontal', 'right', 'left', 'rigth']:
            raise ValueError


class _OutputReviewMov(File):
    """Mov generated from 3 input movs in grid."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to mov file
        """
        super(_OutputReviewMov, self).__init__(file_)
        self.input_movs = []

    def generate(self):
        """Generate mov in current nuke session."""
        if not host.cur_scene() == _REVIEW_MOV_EXPORT_NK:
            host.open_scene(_REVIEW_MOV_EXPORT_NK, force=True)

        for _idx, _mov in enumerate(self.input_movs):
            _node = nuke.toNode('Read{:d}'.format(_idx+1))
            _node['file'].fromUserText(_mov.path)

        _last = _node['last'].value()
        print 'LAST', _last
        nuke.toNode('Write1')['file'].setValue(self.path)
        nuke.render('Write1', 1, _last)


def process_movs_for_review(dir_=None, filter_=None, verbose=0):
    """Process review movs.

    Each set of three input movs in Front/Left/Right/Producer suffix
    is comped into an output mov using the template nk file.

    Args:
        dir_ (str): dir to search from input mov groups
        filter_ (str): apply file path filter
        verbose (int): print process data
    """

    # Get dirs to search
    _today_dir = abs_path(time.strftime(
        r'P:\projects\frasier_38732V\production\vendor_in\Motion Burner'
        r'\%Y-%m-%d'))
    _dirs = set([_today_dir])
    if dir_:
        _dirs.add(abs_path(dir_))
    _dirs = sorted(_dirs)
    print 'SEARCH DIRS:'
    pprint.pprint(_dirs)

    _movs = []
    for _dir in _dirs:
        _movs += find(_dir, type_='f', extn='mov', class_=_InputReviewMov,
                      filter_=filter_)

    # Find review movs
    _review_movs = {}
    for _input_mov in sorted(_movs):
        lprint('ADDING MOV', _input_mov, verbose=verbose)
        _key = _input_mov.review_mov.path.lower()
        if _key not in _review_movs:
            _review_movs[_key] = _input_mov.review_mov
        _review_movs[_key].input_movs.append(_input_mov)
    print 'FOUND {:d} REVIEW MOVS'.format(len(_review_movs))
    for _path, _review_mov in _review_movs.items():
        if _review_mov.exists():
            del _review_movs[_path]
    print '{:d} TO GENERATE'.format(len(_review_movs))

    for _idx, _review_mov in enumerate(sorted(_review_movs.values())):

        print '{:d}/{:d} {}'.format(_idx+1, len(_review_movs), _review_mov)
        for _input_mov in _review_mov.input_movs:
            print ' -', _input_mov
        assert len(_review_mov.input_movs) == 3

        _review_mov.generate()
