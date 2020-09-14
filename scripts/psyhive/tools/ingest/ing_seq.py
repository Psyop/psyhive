"""Tools for managing ingestion of vendor image sequences."""

import time

from transgen import helper

from psyhive import tk2
from psyhive.utils import get_single, Seq, get_time_f, abs_path

from .ing_utils import INGESTED_TOKEN, map_tag_to_shot


def _is_ver(token):
    """Test if the given token is a valid verison (eg. v001).

    Args:
        token (str): token to test

    Returns:
        (bool): whether token is version
    """
    return len(token) == 4 and token[0] == 'v' and token[1:].isdigit()


def _parse_seq_basename(basename):
    """Parse basename of the given image sequence.

    Sequence basenames must follow one of these 3 conventions:

        - <tag>_<step>_<version>
        - <tag>_<step>_<layer>_<version>
        - <tag>_<step>_<layer>_<version>_<aov>

    Args:
        basename (str): basename to parse

    Returns:
        (str tuple): tag/step/layer/version/aov data
    """
    _tokens = basename.split('_')
    _tag, _step = _tokens[:2]
    _ver = get_single([_token for _token in _tokens if _is_ver(_token)])
    _layer = '_'.join(_tokens[2: _tokens.index(_ver)]) or None
    _aov = '_'.join(_tokens[_tokens.index(_ver)+1:]) or None
    return _tag, _step, _layer, _ver, _aov


class VendorSeq(Seq):
    """Base class for a vendor image sequence."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to image sequence
        """
        super(VendorSeq, self).__init__(path)
        _data = _parse_seq_basename(self.basename)
        self.tag, self.step, self.layer, self.version, self.aov = _data
        self.ver_n = int(self.version[1:])

    @property
    def mtime(self):
        """Retrieve delivery date from source file path.

        Returns:
            (float): delivery date
        """
        for _token in reversed(self.path.split('/')):
            _date_str = _token.split('_')[0]
            for _t_fmt in ['%Y-%m-%d']:
                try:
                    _mtime = time.strptime(_date_str, _t_fmt)
                except ValueError:
                    pass
                else:
                    return get_time_f(_mtime)
        raise ValueError('Failed to read delivery date {}'.format(self.path))

    def has_sg_version(self):
        """Test if there is a shotgun version for this seq.

        NOTE: there could be more than one if someone already published it
        through Publish Files tool manually.

        Returns:
            (bool): whether version found in shotgun
        """
        _out = self.to_psy_file_seq()
        _data = tk2.get_sg_data(
            'Version', entity=_out.get_shot().get_sg_data(),
            code=_out.basename, fields=['sg_path_to_frames'])
        if not _data or not _data[0]['sg_path_to_frames']:
            return False
        _path = abs_path(_data[0]['sg_path_to_frames']).replace('####', '%04d')
        print ' - VER PATH', _path
        assert _path == _out.path
        return True

    def to_psy_file_seq(self):
        """Get the psyop output image sequence for this source sequence.

        Returns:
            (TTOutputFileSeq): output file sequence
        """
        _shot = map_tag_to_shot(self.tag)
        if not _shot:
            raise ValueError('Tag {} did not map to any shot'.format(self.tag))
        _step = _task = self.step

        return _shot.map_to(
            tk2.TTOutputFileSeq, extension=self.extn, Task=_task, Step=_step,
            version=self.ver_n, format=self.extn, output_type='render',
            output_name=self.layer, channel=self.aov)

    def get_ingest_status(self, resubmit_transgens):
        """Get ingestion status for this sequence.

        Args:
            resubmit_transgens (bool): resubmit trangen even if
                already submitted

        Returns:
            (str): ingest status
        """

        try:
            _out = self.to_psy_file_seq()
        except ValueError as _exc:
            return _exc.message, False

        print ' - OUTPUT', _out.path

        if _out.cache_read(INGESTED_TOKEN):
            return 'Already ingested', False

        if not _out.exists():
            return 'Ready to ingest', True

        # Check current source matches
        _src = _out.cache_read('vendor_source')
        if _src and not _src == self.path:
            print 'SRC', _src
            raise NotImplementedError
        elif not _src:
            raise NotImplementedError

        # Check for sg published file
        if not _out.get_sg_data():
            return 'Needs register in sg', True

        # Check for sg version
        if not self.has_sg_version():
            if (
                    not resubmit_transgens and
                    _out.cache_read('submitted transgen')):
                return 'Waiting on transgen', False
            return 'Needs sg version publish', True

        _out.cache_write(INGESTED_TOKEN, True)
        return 'Already ingested', False

    def ingest(self, vendor):
        """Ingest this image sequence to psyop pipeline.

        Args:
            vendor (str): source vendor
        """
        _out = self.to_psy_file_seq()
        print ' - OUT', _out.path

        # Create images on psy side
        if not _out.exists():

            # Check asset/shot + step exists
            _root = tk2.TTRoot(_out.path)
            _step = tk2.TTStepRoot(_out.path)
            if not _step.exists():
                _root.create_workspaces(force=True)
            assert _step.exists()
            print ' - STEP EXISTS', _step.path

            # Copy images
            self.copy_to(_out)
            _out.cache_write('vendor_source', self.path)
            print ' - COPIED IMAGES'

        # Publish in shotgun
        if not _out.get_sg_data():
            _comment = 'From {} {}'.format(vendor, time.strftime('%m/%d/%y'))
            print ' - COMMENT', _comment
            _out.register_in_shotgun(comment=_comment, complete=True)

        # Transgen
        if not self.has_sg_version():
            _start, _end = _out.find_range()
            helper.process_submission_preset(
                _out.path, _start, _end, 'dailies-scene-referred',
                submit_to_farm=True)
            _out.cache_write('submitted transgen', True)
