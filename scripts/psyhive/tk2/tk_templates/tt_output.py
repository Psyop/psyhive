"""Tools for managing tank template output representations."""

import operator
import pprint

import tank

from psyhive import pipe
from psyhive.utils import (
    File, abs_path, lprint, apply_filter, Seq, seq_from_frame,
    get_single, Movie)

from .tt_base import TTDirBase, TTBase
from .tt_utils import get_area, get_template


class TTOutputType(TTDirBase):
    """Represents an output type directory."""

    hint_fmt = '{area}_output_type'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output type dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTOutputType, self).__init__(path, hint=_hint)

    def find_names(self, class_=None, filter_=None, output_name=None,
                   task=None, verbose=0):
        """Find output names in this type dir.

        Args:
            class_ (class): override output name class
            filter_ (str): filter by path
            output_name (str): filter by output name
            task (str): filter by task
            verbose (int): print process data

        Returns:
            (TTOutputName list): list of output names
        """
        _names = self._read_names(class_=class_)
        lprint(' - FOUND {:d} NAMES'.format(len(_names)), verbose=verbose)

        if filter_:
            lprint(' - APPLYING FILTER', len(_names), verbose=verbose)
            _names = apply_filter(
                _names, filter_, key=operator.attrgetter('path'))

        if output_name is not None:
            lprint(' - APPLYING NAME FILTER', len(_names), verbose=verbose)
            _names = [_name for _name in _names
                      if _name.output_name == output_name]

        if task is not None:
            lprint(' - APPLYING TASK FILTER', len(_names), verbose=verbose)
            _names_copy = _names[:]
            _names = []
            for _name in _names_copy:
                if _name.task != task:
                    lprint('   - REJECTED', _name, verbose=verbose)
                    continue
                lprint('   - ACCEPTED', _name, verbose=verbose)
                _names.append(_name)

        lprint(' - FOUND {:d} MATCHING NAMES'.format(len(_names)),
               verbose=verbose)
        return _names

    def _read_names(self, class_=None):
        """Read output names from dist.

        Args:
            class_ (class): override output name class

        Returns:
            (TTOutputName list): list of output names
        """
        return self.find(depth=1, class_=class_ or TTOutputName)


class TTOutputName(TTDirBase):
    """Represents an output name dir on disk."""

    hint_fmt = '{area}_output_name'
    task = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output name dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTOutputName, self).__init__(path, hint=_hint)

    def find_latest(self):
        """Find latest version of this output.

        Returns:
            (TTOutputVersionBase): latest version
        """
        _vers = self.find_versions()
        if not _vers:
            return None
        return _vers[-1]

    def find_versions(self, class_=None, version=None, filter_=None):
        """Find versions of this output name.

        Args:
            class_ (class): override output version class
            version (int): filter by version
            filter_ (str): filter file path

        Returns:
            (TTOutputVersion list): list of versions
        """
        _vers = self._read_versions(class_=class_)

        # Apply version filter
        if version == 'latest' and _vers:
            _vers = [_vers[-1]]
        elif version is not None:
            _vers = [_ver for _ver in _vers if _ver.version == version]

        if filter_:
            _vers = apply_filter(_vers, filter_,
                                 key=operator.attrgetter('path'))
        return _vers

    def _read_versions(self, class_=None):
        """Read versions of this output name from disk.

        Args:
            class_ (class): override output version class

        Returns:
            (TTOutputVersion list): list of versions
        """
        return self.find(depth=1, class_=class_ or TTOutputVersion)


class TTOutputVersion(TTDirBase):
    """Represents an output version dir."""

    hint_fmt = '{area}_output_version'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output version dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTOutputVersion, self).__init__(path, hint=_hint)

    def find_file(self, extn=None, format_=None, catch=False):
        """Find output file within this version dir.

        Args:
            extn (str): filter by extension
            format_ (str): filter by format
            catch (bool): no error if exactly one file wasn't matched

        Returns:
            (TTOutputFile|TTOutputFileSeq): matching output file
        """
        _files = self.find_files(extn=extn, format_=format_)
        return get_single(_files, verbose=1, catch=catch)

    def find_files(self, extn=None, format_=None, class_=None):
        """Find output files within this version dir.

        Args:
            extn (str): filter by extension
            format_ (str): filter by format
            class_ (class): filter by class

        Returns:
            (TTOutputFile|TTOutputFileSeq list): matching output files
        """
        return sum([_out.find_files(extn=extn, format_=format_, class_=class_)
                    for _out in self.find_outputs()], [])

    def find_latest(self):
        """Find latest version of this output.

        Returns:
            (TTOutputVersion): latest version
        """
        _name = TTOutputName(self.path)
        for _o_ver in reversed(_name.find_versions()):
            if _o_ver == self:
                return self
            _out = self.map_to(version=_o_ver.version)
            if _out.exists():
                return _out
        raise OSError('Failed to find latest version '+self.path)

    def find_outputs(self, filter_=None):
        """Find outputs within this version dir.

        Args:
            filter_ (str): filter by path

        Returns:
            (TTOutput list): list of outputs
        """
        _outs = self._read_outputs()
        if filter_:
            _outs = apply_filter(
                _outs, filter_, key=operator.attrgetter('path'))
        return _outs

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.find_latest() == self

    def _read_outputs(self, class_=None):
        """Read outputs within this version dir from disk.

        Args:
            class_ (class): override output class

        Returns:
            (TTOutput list): list of outputs
        """
        return self.find(depth=1, class_=class_ or TTOutput)


class TTOutput(TTDirBase):
    """Represents an output dir."""

    hint_fmt = '{area}_output'

    format = None
    output_name = None
    version = None

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTOutput, self).__init__(path, hint=_hint)

    def find_file(self, extn=None, verbose=1):
        """Find single matching file within this output.

        Args:
            extn (str): filter by extension
            verbose (int): print process data

        Returns:
            (TTOutputFileBase): matching file
        """
        return get_single(self.find_files(extn=extn), verbose=verbose)

    def find_files(self, extn=None, format_=None, class_=None, verbose=0):
        """Find output files/seqs within this output dir.

        Args:
            extn (str): filter by extension
            format_ (str): filter by format
            class_ (str): filter by class
            verbose (int): print process data

        Returns:
            (TTOutputFile|TTOutputFileSeq list): output files/seqs
        """
        _files = self._read_files(verbose=verbose)
        if extn is not None:
            _files = [_file for _file in _files if _file.extn == extn]
        if format_ is not None:
            _files = [_file for _file in _files if _file.format == format_]
        if class_:
            _files = [_file for _file in _files if isinstance(_file, class_)]
        return _files

    def find_latest(self):
        """Find latest version of this output.

        Returns:
            (TTOutput): latest version
        """
        _ver = TTOutputVersion(self.path)
        _name = TTOutputName(self.path)
        for _o_ver in reversed(_name.find_versions()):
            if _o_ver == _ver:
                return self
            _out = self.map_to(version=_o_ver.version)
            if _out.exists():
                return _out
        return None  # Consistent with TTWork.find_latest

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.find_latest() == self

    def _read_files(self, verbose=0):
        """Read files/seqs within this output from disk.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputFile|TTOutputFileSeq list): output files/seqs
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
                    lprint(' - EXISTING SEQ', _file, verbose=verbose > 2)
                    break
            if _already_matched:
                continue

            _output = None
            lprint(' - TESTING', _file, verbose=verbose > 1)

            # Match seq
            _seq = seq_from_frame(_file, catch=True)
            if _seq:
                try:
                    _output = TTOutputFileSeq(_seq.path)
                except ValueError:
                    lprint('   - NOT TTOutputFileSeq', _file,
                           verbose=verbose > 1)
                else:
                    _frame = _output.get_frame(_file)
                    _seqs[_output] = set([_frame])
            else:
                lprint('   - NOT OUTPUT FILE SEQ', _file,
                       verbose=verbose > 1)

            # Match file
            if not _output:
                try:
                    _output = TTOutputFile(_file)
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


class _TTOutputFileBase(TTBase):
    """Base class for any output file/seq."""

    channel = None
    extension = None
    task = None
    version = None

    def find_latest(self):
        """Find latest version of this output.

        Returns:
            (TTOutputFileBase): latest version
        """
        _ver = TTOutputVersion(self.path)
        _name = TTOutputName(self.path)
        for _o_ver in reversed(_name.find_versions()):
            if _o_ver == _ver:
                return self
            _out = self.map_to(version=_o_ver.version)
            if _out.exists():
                return _out
        return None  # Consistent with TTWork.find_latest

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.find_latest() == self

    def get_sg_data(self, verbose=0):
        """Find shotgun data for this publish.

        Args:
            verbose (int): print process data

        Returns:
            (dict): shoutgun data
        """
        from psyhive import tk2
        _proj = tk2.get_project_sg_data(pipe.Project(self.path))
        _root = tk2.TTRoot(self.path)
        _task = tk2.get_sg_data(
            'Task', content=self.task, project=_proj,
            entity=_root.get_sg_data())
        _data = tk2.get_sg_data(
            'PublishedFile', version_number=self.ver_n, sg_format=self.extn,
            project=_proj, task=_task, limit=2,
            code=self.filename.replace('%04d', '####'),
            fields=['task', 'code', 'short_name'])
        if verbose:
            pprint.pprint(_data)
        if len(_data) > 1:
            raise RuntimeError(self.path)
        return get_single(_data, catch=True)

    def move_to(self, trg, force=False):
        """Needs to be implemented in subclass.

        Args:
            trg (str): new location
            force (bool): replace any existing file without confirmation
        """
        raise NotImplementedError

    def register_in_shotgun(self, complete=False, verbose=0, **kwargs):
        """Register this output in shotgun.

        Args:
            complete (bool): complete status
            verbose (int): print process data
        """
        from psyhive import tk2

        # Get tank apps/modules
        _fileops = tk2.find_tank_app('psy-multi-fileops')
        _workspace_fo = tk2.find_tank_mod(
            'workspace', app='psy-multi-fileops')
        _workspace_sg = tk2.find_tank_mod(
            "shotgun", app="psy-framework-workspace")
        _framework_sg = tk2.find_tank_mod(
            'shotgun', app='psy-framework-publish')

        # Create workspace
        _work = self.map_to(tk2.TTWork, dcc='maya', extension='ma')
        lprint(' - WORK', _work, verbose=verbose)
        _fo_workspace = _workspace_fo.get_workspace_from_path(
            app=_fileops, path=_work.path)  # To access context
        lprint(' - FILEOPS WORKSPACE', _fo_workspace, verbose=verbose)
        _sg_workspace = _workspace_sg.workspace_from_context(
            _fo_workspace.context)
        lprint(' - SG WORKSPACE', _sg_workspace, verbose=verbose)

        # Register
        _path = self.path.replace(".%04d.", ".####.")
        _framework_sg.register_publish(
            _path, complete=complete, workspace=_sg_workspace, **kwargs)

    @property
    def ver_n(self):
        """Get this output's version number as an integer.

        Returns:
            (int): version
        """
        return int(self.version)


class TTOutputFile(_TTOutputFileBase, File):
    """Represents an output file."""

    hint_fmt = '{area}_output_file'
    move_to = File.move_to

    def __init__(self, file_, verbose=0):
        """Constructor.

        Args:
            file_ (str): path to output file
            verbose (int): print process data
        """
        File.__init__(self, file_)
        _path = abs_path(file_)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)
        super(TTOutputFile, self).__init__(file_, hint=_hint, verbose=verbose)

    def view(self):
        """View this movie file."""
        Movie(self.path).view()


class TTOutputFileSeq(_TTOutputFileBase, Seq):
    """Represents an output file sequence."""

    hint_fmt = '{area}_output_file_seq'

    exists = Seq.exists
    move_to = Seq.move_to

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): path to output file seq
            verbose (int): print process data
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = self.hint_fmt.format(area=_area)

        _tmpl = get_template(_hint)
        try:
            _data = _tmpl.get_fields(_path)
        except tank.TankError as _exc:
            lprint('TANK ERROR', _exc.message, verbose=verbose)
            raise ValueError("Tank rejected path "+path)
        _data["SEQ"] = "%04d"
        _path = abs_path(_tmpl.apply_fields(_data))

        super(TTOutputFileSeq, self).__init__(_path, hint=_hint)
        Seq.__init__(self, path)
