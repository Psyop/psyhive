"""Tools relating to tank templates within shots."""

import tank

from tank.platform import current_engine

from psyhive import pipe
from psyhive.utils import find, Seq, abs_path

from psyhive.tk.templates.misc import get_template
from psyhive.tk.templates.base import (
    TTBase, TTDirBase, TTWorkAreaBase, TTWorkFileBase, TTOutputVerBase,
    TTRootBase, TTStepRootBase)


class _TTShotChildBase(object):
    """Base class for any template inside a shot."""

    path = None

    @property
    def shot(self):
        """This object's shot."""
        return TTShotRoot(self.path)


class TTSequenceRoot(TTDirBase):
    """Represents a tank template sequence root."""

    hint = 'sequence_root'
    sequence = None

    def find_shots(self, class_=None):
        """Find shots in this sequence.

        Args:
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
            _shots.append(_shot)
        return _shots

    @property
    def name(self):
        """Get step type."""
        return self.sequence


class TTShotRoot(TTRootBase):
    """Represents a tank template shot root."""

    hint = 'shot_root'
    shot = None

    @property
    def name(self):
        """Get step type."""
        return self.shot

    @property
    def step_type(self):
        """Get step type."""
        return TTShotStepRoot


class TTShotStepRoot(TTStepRootBase, _TTShotChildBase):
    """Represents a tank template shot step root."""

    hint = 'shot_step_root'
    work_area_maya_hint = 'shot_work_area_maya'

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

    @property
    def work_area_maya_type(self):
        """Get work area type."""
        return TTShotWorkAreaMaya


class TTShotWorkAreaMaya(TTWorkAreaBase, _TTShotChildBase):
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


class TTMayaShotWork(TTWorkFileBase, _TTShotChildBase):
    """Represents a maya shot work file tank template."""

    hint = 'maya_shot_work'
    work_area_type = TTShotWorkAreaMaya


class TTMayaShotIncrement(TTBase, _TTShotChildBase):
    """Represents a maya work file increment file tank template."""

    hint = 'maya_shot_increment'

    def get_work(self):
        """Get work file this increment belongs to.

        Returns:
            (TTMayaShotWork): work file
        """
        _tmpl = current_engine().tank.templates['maya_shot_work']
        _path = _tmpl.apply_fields(self.data)
        return TTMayaShotWork(_path)


class TTShotOutputRoot(TTDirBase, _TTShotChildBase):
    """Represents a shot output root tank template path."""

    hint = 'shot_output_root'


class TTShotOutputType(TTDirBase, _TTShotChildBase):
    """Represents a shot output type tank template path."""

    hint = 'shot_output_type'


class TTShotOutputName(TTDirBase, _TTShotChildBase):
    """Represents a shot output name tank template path.

    This is the tank template for the versions dir.
    """

    hint = 'shot_output_name'


class TTShotOutputVersion(TTOutputVerBase, _TTShotChildBase):
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


class TTShotOutputFileSeq(TTBase, _TTShotChildBase, Seq):
    """Represents a shout output file seq tank template path."""

    hint = 'shot_output_file_seq'

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): file seq path
        """
        _tmpl = get_template(self.hint)
        try:
            _data = _tmpl.get_fields(path)
        except tank.TankError:
            raise ValueError
        _data["SEQ"] = "%04d"
        _path = abs_path(_tmpl.apply_fields(_data))
        super(TTShotOutputFileSeq, self).__init__(
            path=_path, data=_data, tmpl=_tmpl)
        Seq.__init__(self, _path)


def get_shot(path):

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
