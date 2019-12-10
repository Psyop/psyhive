"""Tools for managing tank template output representations."""

import operator

import tank

from psyhive.utils import (
    File, abs_path, lprint, apply_filter, Seq, seq_from_frame)

from psyhive.tk2.tk_templates.tt_base import TTDirBase, TTBase
from psyhive.tk2.tk_templates.tt_utils import get_area, get_template


class TTOutputType(TTDirBase):
    """Represents an output type directory."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output type dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_output_type'.format(_area)
        super(TTOutputType, self).__init__(path, hint=_hint)

    def find_names(self, class_=None, filter_=None, output_name=None,
                   task=None):
        """Find output names in this type dir.

        Args:
            class_ (class): override output name class
            filter_ (str): filter by path
            output_name (str): filter by output name
            task (str): filter by task

        Returns:
            (TTOutputName list): list of output names
        """
        _names = self._read_names(class_=class_)
        if filter_:
            _names = apply_filter(
                _names, filter_, key=operator.attrgetter('path'))
        if output_name is not None:
            _names = [_name for _name in _names
                      if _name.output_name == output_name]
        if task is not None:
            _names = [_name for _name in _names
                      if _name.task == task]

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

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output name dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_output_name'.format(_area)
        super(TTOutputName, self).__init__(path, hint=_hint)

    def find_versions(self, class_=None, version=None):
        """Find versions of this output name.

        Args:
            class_ (class): override output version class
            version (int): filter by version

        Returns:
            (TTOutputVersion list): list of versions
        """
        _vers = self._read_versions(class_=class_)
        if version is not None:
            _vers = [_ver for _ver in _vers if _ver.version == version]
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

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output version dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_output_version'.format(_area)
        super(TTOutputVersion, self).__init__(path, hint=_hint)

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

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to output dir
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_output'.format(_area)
        super(TTOutput, self).__init__(path, hint=_hint)

    def find_files(self, verbose=0):
        """Find output files/seqs within this output dir.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputFile|TTOutputFileSeq list): output files/seqs
        """
        return self._read_files(verbose=verbose)

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


class TTOutputFile(TTBase, File):
    """Represents an output file."""

    channel = None

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to output file
        """
        File.__init__(self, file_)
        _path = abs_path(file_)
        _area = get_area(_path)
        _hint = '{}_output_file'.format(_area)
        super(TTOutputFile, self).__init__(file_, hint=_hint)


class TTOutputFileSeq(TTBase, Seq):
    """Represents an output file sequence."""

    channel = None

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): path to output file seq
            verbose (int): print process data
        """
        _path = abs_path(path)
        _area = get_area(_path)
        _hint = '{}_output_file_seq'.format(_area)

        _tmpl = get_template(_hint)
        try:
            _data = _tmpl.get_fields(_path)
        except tank.TankError as _exc:
            lprint('TANK ERROR', _exc.message, verbose=verbose)
            raise ValueError("Tank rejected path "+path)
        _data["SEQ"] = "%04d"
        _path = abs_path(_tmpl.apply_fields(_data))

        Seq.__init__(self, path)
        super(TTOutputFileSeq, self).__init__(_path, hint=_hint)
