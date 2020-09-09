"""Tools for managing ingestion of vendor image sequences."""

import time

from psyhive import tk2
from psyhive.utils import get_single, Seq, get_time_f

from . import ing_utils


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

    def to_psy_file_seq(self):
        """Get the psyop output image sequence for this source sequence.

        Returns:
            (TTOutputFileSeq): output file sequence
        """
        _shot = ing_utils.map_tag_to_shot(self.tag)
        if not _shot:
            raise ValueError('Tag {} did not map to any shot'.format(self.tag))
        _step = _task = self.step

        return _shot.map_to(
            tk2.TTOutputFileSeq, extension=self.extn, Task=_task, Step=_step,
            version=self.ver_n, format=self.extn, output_type='render',
            output_name=self.layer, channel=self.aov,
        )

    def ingest(self, vendor):
        """Ingest this image sequence to psyop pipeline.

        Args:
            vendor (str): source vendor
        """
        _out = self.to_psy_file_seq()

        # Check asset/shot + step exists
        _root = tk2.TTRoot(_out.path)
        if not _root.exists():
            _root.create_workspaces()
        _step = tk2.TTStepRoot(_out.path)
        assert _step.exists()

        # Copy images
        self.copy_to(_out)
        _out.cache_write('vendor_source', self.path)

        # Publish in shotgun
        _comment = 'From {} {}'.format(vendor, time.strftime('%m/%d/%y'))
        print _comment
        _out.register_in_shotgun(comment=_comment, complete=True)
