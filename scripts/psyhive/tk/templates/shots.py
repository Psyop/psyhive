"""Tools relating to tank templates within shots."""

from psyhive import pipe
from psyhive.utils import find, passes_filter

from psyhive.tk.templates.misc import get_template
from psyhive.tk.templates.base import (
    TTDirBase, TTWorkAreaBase, TTWorkFileBase, TTOutputVersionBase,
    TTRootBase, TTStepRootBase, TTOutputFileSeqBase, TTWorkIncrementBase,
    TTOutputFileBase)


class _TTShotCpntBase(object):
    """Base class for any template inside a shot."""

    path = None

    @property
    def maya_inc_type(self):
        """Get maya work increment type."""
        return TTMayaShotIncrement

    @property
    def maya_work_type(self):
        """Get maya work type."""
        return TTMayaShotWork

    @property
    def output_root_type(self):
        """Get output root type."""
        return TTShotOutputRoot

    @property
    def output_name_type(self):
        """Get output name type."""
        return TTShotOutputName

    @property
    def output_version_type(self):
        """Get output version type."""
        return TTShotOutputVersion

    @property
    def output_file_seq_type(self):
        """Get output file seq type."""
        return TTShotOutputFileSeq

    @property
    def output_file_type(self):
        """Get output file type."""
        return TTShotOutputFile

    @property
    def shot(self):
        """This object's shot."""
        return TTShotRoot(self.path)

    @property
    def step_root_type(self):
        """Get step root type."""
        return TTShotStepRoot

    @property
    def work_area_maya_type(self):
        """Get work area maya type."""
        return TTShotWorkAreaMaya


class TTSequenceRoot(TTDirBase):
    """Represents a tank template sequence root."""

    hint = 'sequence_root'
    sequence = None

    def find_shots(self, filter_=None, class_=None):
        """Find shots in this sequence.

        Args:
            filter_ (str): filter by shot name
            class_ (TTShotRoot): override shot class

        Returns:
            (TTShotRoot list): list of shots
        """
        _shots = []
        _class = class_ or TTShotRoot
        for _path in self.find(depth=1):
            try:
                _shot = _class(_path)
            except ValueError:
                continue
            if filter_ and not passes_filter(_shot.name, filter_):
                continue
            _shots.append(_shot)
        return _shots

    @property
    def name(self):
        """Get step type."""
        return self.sequence


class TTShotRoot(_TTShotCpntBase, TTRootBase):
    """Represents a tank template shot root."""

    hint = 'shot_root'
    shot = None

    @property
    def name(self):
        """Get step type."""
        return self.shot


class TTShotStepRoot(_TTShotCpntBase, TTStepRootBase):
    """Represents a tank template shot step root."""

    hint = 'shot_step_root'
    work_area_maya_hint = 'shot_work_area_maya'
    # work_area_maya_type = _TTShotCpntBase.work_area_maya_type

    def find_output_vers(self):
        """Find output versions in this shot.

        Returns:
            (TTShotOutputVersion list): list of output versions
        """
        _tmpl = get_template('shot_output_root')
        _out_root = TTShotOutputRoot(_tmpl.apply_fields(self.data))
        _vers = []
        for _dir in _out_root.find(depth=1, type_='d'):
            _type = TTShotOutputType(_dir)
            for _dir in _type.find(depth=1, type_='d'):
                try:
                    _name = TTShotOutputName(_dir)
                except ValueError:
                    continue
                for _dir in _name.find(depth=1, type_='d'):
                    _ver = TTShotOutputVersion(_dir)
                    _vers.append(_ver)
        return _vers

    # @property
    # def maya_work(self):
    #     """Get work area type for maya."""
    #     return TTMayaShotWork

    # @property
    # def work_area_maya_type(self):
    #     """Get work area type."""
    #     return TTShotWorkAreaMaya


class TTShotWorkAreaMaya(TTWorkAreaBase, _TTShotCpntBase):
    """Represents a tank template shot work area for maya."""

    hint = 'shot_work_area_maya'

    def find_work_files(self):
        """Find work files in this shot area.

        Returns:
            (TTMayaShotWork list): list of work files
        """
        _work_files = []
        for _file in self.find(depth=2, type_='f'):
            try:
                _work = TTMayaShotWork(_file)
            except ValueError:
                continue
            _work_files.append(_work)

        return _work_files


class TTMayaShotWork(_TTShotCpntBase, TTWorkFileBase):
    """Represents a maya shot work file tank template."""

    hint = 'maya_shot_work'
    work_area_type = TTShotWorkAreaMaya


class TTMayaShotIncrement(_TTShotCpntBase, TTWorkIncrementBase):
    """Represents a maya work file increment file tank template."""

    hint = 'maya_shot_increment'


class TTShotOutputRoot(_TTShotCpntBase, TTDirBase):
    """Represents a shot output root tank template path."""

    hint = 'shot_output_root'


class TTShotOutputType(_TTShotCpntBase, TTDirBase):
    """Represents a shot output type tank template path."""

    hint = 'shot_output_type'


class TTShotOutputName(_TTShotCpntBase, TTDirBase):
    """Represents a shot output name tank template path.

    This is the tank template for the versions dir.
    """

    hint = 'shot_output_name'


class TTShotOutputVersion(_TTShotCpntBase, TTOutputVersionBase):
    """Represents a shot output version tank template path."""

    output_name = None
    hint = 'shot_output_version'
    output_type = None

    def get_display_tags(self):
        """Get display tags for this version.

        Returns:
            (tuple): display data
        """
        return (
            self.output_type, self.step, self.task, self.output_name,
            self.get_status())


class TTShotOutputFile(_TTShotCpntBase, TTOutputFileBase):
    """Base class for any output file tank template."""

    hint = 'shot_output_file'


class TTShotOutputFileSeq(_TTShotCpntBase, TTOutputFileSeqBase):
    """Represents a shot output file seq tank template path."""

    hint = 'shot_output_file_seq'


def get_shot(path):
    """Get a shot object from the given path.

    Args:
        path (str): path to test

    Returns:
        (TTShotRoot|None): shot root (if any)
    """
    try:
        return TTShotRoot(path)
    except ValueError:
        return None


def find_sequences():
    """Find sequences in the current project.

    Returns:
        (TTSequenceRoot): list of sequences
    """
    _seq_path = pipe.cur_project().path+'/sequences'
    _seqs = []
    for _path in find(_seq_path, depth=1):
        _seq = TTSequenceRoot(_path)
        _seqs.append(_seq)
    return _seqs


def find_shots(class_=None):
    """Find shots in the current job.

    Args:
        class_ (class): override shot root class

    Returns:
        (TTShotRoot): list of shots
    """
    return sum([
        _seq.find_shots(class_=class_)
        for _seq in find_sequences()], [])
