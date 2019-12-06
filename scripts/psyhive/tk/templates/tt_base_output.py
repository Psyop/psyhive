"""Base classes for tank templates output data."""

import os
import tank

from psyhive.utils import File, abs_path, find, lprint, Seq

from psyhive.tk.templates.tt_base import TTDirBase, TTBase
from psyhive.tk.templates.tt_misc import get_template


class TTOutputNameBase(TTDirBase):
    """Base class for any tank template output name."""

    output_version_type = None
    step_root_type = None

    def find_latest(self, catch=False):
        """Find latest version of this output.

        Args:
            catch (bool): no error if no versions found

        Returns:
            (TTOutputVersionBase): latest version
        """
        _vers = self.find_vers(catch=catch)
        if not _vers:
            return None
        return _vers[-1]

    def find_vers(self, catch=False):
        """Find versions in this output.

        Args:
            catch (bool): no error if no versions found

        Returns:
            (TTOutputVersionBase list): versions
        """
        _vers = find(self.path, depth=1, type_='d',
                     class_=self.output_version_type)
        if not _vers:
            if catch:
                return None
            raise OSError("No versions found")
        return _vers

    def get_step_root(self):
        """Get step root from this output name.

        Returns:
            (TTStepRootBase): step root
        """
        return self.step_root_type(self.path)


class TTOutputVersionBase(TTDirBase):
    """Base class for any tank template version dir."""

    maya_work_type = None
    output_file_seq_type = None
    output_file_type = None
    output_name_type = None
    step_root_type = None
    task = None
    version = None

    def find_latest(self, catch=False):
        """Find latest version.

        Args:
            catch (bool): no error if no versions found

        Returns:
            (TTOutputVersionBase): latest version
        """
        _name = self.map_to(self.output_name_type)
        return _name.find_latest(catch=catch)

    def find_outputs(self, output_type=None, output_name=None, format_=None,
                     thumbs=False, verbose=0):
        """Find outputs in this version.

        Args:
            output_type (str): filter by output_type
            output_name (str): filter by output_name
            format_ (str): filter by format
            thumbs (bool): include thumbs
            verbose (int): print process data

        Returns:
            (TTOutputFileBase|TTOutputFileSeqBase list): outputs
        """
        lprint('SEARCHING FOR OUTPUTS', verbose=verbose)

        _outputs = []
        for _output in self._read_outputs():
            if output_name and not _output.output_name == output_name:
                continue
            elif output_type and not _output.output_type == output_type:
                continue
            elif format_ and not _output.format == format_:
                continue
            if not thumbs and _output.data.get('channel') == '.thumbs':
                continue
            lprint(' - ADDED OUTPUT', _output, verbose=verbose)
            _outputs.append(_output)

        return _outputs

    def find_work_file(self, verbose=1):
        """Find work file this output was generated from.

        Args:
            verbose (int): print process data

        Returns:
            (TTWorkFileBase|None): associated work file (if any)
        """
        for _extn in ['ma', 'mb']:
            _work = self.map_to(self.maya_work_type, extension=_extn)
            lprint(' - CHECKING WORK', _work, verbose=verbose)
            if _work.exists():
                return _work
        return None

    def get_status(self):
        """Generate status for this version.

        Returns:
            (str): version status
        """
        _latest = self.find_latest()
        if self == _latest:
            return 'up to date'
        return 'needs update (latest:v{:03d})'.format(_latest.version)

    def get_step_root(self):
        """Get this output version's step root.

        Returns:
            (TTStepRootBase): step root
        """
        return self.map_to(self.step_root_type)

    def is_latest(self):
        """Test whether this version is the latest.

        Returns:
            (bool): latest state
        """
        return self == self.find_latest()

    @property
    def name(self):
        """Get version name (eg. v001).

        Returns:
            (str): version name
        """
        return self.filename

    def _read_outputs(self, verbose=0):
        """Find outputs in this version.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputFileBase list): outputs
        """
        lprint('SEARCHING FOR OUTPUTS', verbose=verbose)

        _files = self.find(type_='f', depth=3)
        lprint(' - FOUND {:d} FILES'.format(len(_files)), verbose=verbose)

        # Map files to outputs
        _outputs = []
        _seqs = {}
        for _file in _files:

            # Ignore files already matched in seq
            _already_matched = False
            for _seq in _seqs:
                if _seq.contains(_file):
                    _already_matched = True
                    _frame = _seq.get_frame(_file)
                    _seqs[_seq].add(_frame)
                    break
            if _already_matched:
                continue

            _output = None
            lprint(' - TESTING', _file, verbose=verbose > 1)

            # Match seq
            try:
                _output = self.output_file_seq_type(_file)
            except ValueError:
                lprint('   - NOT OUTPUT FILE SEQ', _file,
                       verbose=verbose > 1)
            else:
                _frame = _output.get_frame(_file)
                _seqs[_output] = set([_frame])

            # Match file
            if not _output:
                try:
                    _output = self.output_file_type(_file)
                except ValueError:
                    lprint('   - NOT OUTPUT FILE', _file,
                           verbose=verbose > 1)

            if not _output:
                continue

            lprint(' - ADDED OUTPUT', _output, verbose=verbose)
            _outputs.append(_output)

        # Apply frames cache
        for _seq, _frames in _seqs.items():
            _seq.set_frames(sorted(_frames))

        return _outputs

    @property
    def vers_dir(self):
        """Stores directory containing versions."""
        return os.path.dirname(self.path)


class TTOutputInstanceBase(TTBase):
    """Base class for any output leaf node (eg. file/seq)."""

    channel = None
    output_name = None
    output_type = None
    output_version_type = None

    def find_latest(self, catch=False):
        """Get latest version asset stream.

        Args:
            catch (bool): no error if no versions found

        Returns:
            (TTAssetOutputFile): latest asset output file
        """
        _ver = self.output_version_type(self.path)
        _latest = _ver.find_latest(catch=catch)
        if not _latest:
            return None
        return self.map_to(version=_latest.version)

    def find_work_file(self, verbose=1):
        """Find work file corresponding to this seq.

        Args:
            verbose (int): print process data

        Returns:
            (TTWorkFileBase): work file
        """
        _ver = self.output_version_type(self.path)
        return _ver.find_work_file(verbose=verbose)

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.find_latest() == self


class TTOutputFileBase(TTOutputInstanceBase, File):
    """Base class for any output file tank template."""


class TTOutputFileSeqBase(TTOutputInstanceBase, Seq):
    """Represents a shout output file seq tank template path."""

    exists = Seq.exists

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): file seq path
            verbose (int): print process data
        """
        _tmpl = get_template(self.hint)
        try:
            _data = _tmpl.get_fields(path)
        except tank.TankError as _exc:
            lprint('TANK ERROR', _exc.message, verbose=verbose)
            raise ValueError("Tank rejected path "+path)
        _data["SEQ"] = "%04d"
        _path = abs_path(_tmpl.apply_fields(_data))
        super(TTOutputFileSeqBase, self).__init__(
            path=_path, data=_data, tmpl=_tmpl)
        Seq.__init__(self, _path)
