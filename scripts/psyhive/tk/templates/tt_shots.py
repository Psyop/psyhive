"""Tools relating to tank templates within shots."""

import tank

from psyhive import pipe
from psyhive.utils import find, passes_filter, get_single

from psyhive.tk.templates.tt_misc import get_template
from psyhive.tk.templates.tt_base import (
    TTRootBase, TTStepRootBase, TTDirBase)
from psyhive.tk.templates.tt_base_work import (
    TTWorkAreaBase, TTWorkFileBase, TTWorkIncrementBase)
from psyhive.tk.templates.tt_base_output import (
    TTOutputVersionBase, TTOutputFileSeqBase, TTOutputFileBase,
    TTOutputNameBase)


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
    def output_type_type(self):
        """Get output name type."""
        return TTShotOutputType

    @property
    def output_version_type(self):
        """Get output version type."""
        return TTShotOutputVersion

    @property
    def output_type_(self):
        """Get output type."""
        return TTShotOutput

    @property
    def output_file_seq_type(self):
        """Get output file seq type."""
        return TTShotOutputFileSeq

    @property
    def output_file_type(self):
        """Get output file type."""
        return TTShotOutputFile

    @property
    def root(self):
        """This object's shot."""
        return self.shot

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

    def get_frame_range(self):
        """Read shot frame range from shotgun.

        Returns:
            (tuple): start/end frames
        """
        from psyhive import tk
        _shotgun = tank.platform.current_engine().shotgun
        _fields = ["sg_head_in", "sg_tail_out"]
        _sg_data = _shotgun.find_one(
            "Shot", filters=[
                ["project", "is", [tk.get_project_data(self.project)]],
                ["code", "is", self.name],
            ],
            fields=_fields)
        return tuple([_sg_data[_field] for _field in _fields])

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


class TTShotWorkAreaHoudini(_TTShotCpntBase, TTWorkAreaBase):
    """Represents a tank template shot work area for houdini."""

    hint = 'shot_work_area_houdini'

    @property
    def work_type(self):
        """Get work file object type.

        Returns:
            (class): work file type
        """
        return TTHoudiniShotWork


class TTHoudiniShotWork(_TTShotCpntBase, TTWorkFileBase):
    """Represents a houdini shot work file tank template."""

    hint = 'houdini_shot_work'
    work_area_type = TTShotWorkAreaHoudini


class TTHoudiniShotIncrement(_TTShotCpntBase, TTWorkIncrementBase):
    """Represents a houdini work file increment file tank template."""

    hint = 'houdini_shot_increment'


class TTShotWorkAreaMaya(_TTShotCpntBase, TTWorkAreaBase):
    """Represents a tank template shot work area for maya."""

    hint = 'shot_work_area_maya'

    @property
    def work_type(self):
        """Get work file object type.

        Returns:
            (class): work file type
        """
        return TTMayaShotWork


class TTMayaShotWork(_TTShotCpntBase, TTWorkFileBase):
    """Represents a maya shot work file tank template."""

    hint = 'maya_shot_work'
    work_area_type = TTShotWorkAreaMaya


class TTMayaShotIncrement(_TTShotCpntBase, TTWorkIncrementBase):
    """Represents a maya work file increment file tank template."""

    hint = 'maya_shot_increment'


class TTShotWorkAreaNuke(TTWorkAreaBase, _TTShotCpntBase):
    """Represents a tank template shot work area for nuke."""

    hint = 'shot_work_area_nuke'

    @property
    def work_type(self):
        """Get work file object type.

        Returns:
            (class): work file type
        """
        return TTNukeShotWork


class TTNukeShotWork(_TTShotCpntBase, TTWorkFileBase):
    """Represents a nuke shot work file tank template."""

    hint = 'nuke_shot_work'
    work_area_type = TTShotWorkAreaNuke


class TTNukeShotIncrement(_TTShotCpntBase, TTWorkIncrementBase):
    """Represents a nuke work file increment file tank template."""

    hint = 'nuke_shot_increment'


class TTShotOutputRoot(_TTShotCpntBase, TTDirBase):
    """Represents a shot output root tank template path."""

    hint = 'shot_output_root'


class TTShotOutputType(_TTShotCpntBase, TTDirBase):
    """Represents a shot output type tank template path."""

    hint = 'shot_output_type'


class TTShotOutputName(_TTShotCpntBase, TTOutputNameBase):
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


class TTShotOutput(_TTShotCpntBase, TTDirBase):
    """Represents a shot output tank template."""

    hint = 'shot_output'


class TTShotOutputFile(_TTShotCpntBase, TTOutputFileBase):
    """Represents a shot output file tank template."""

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


def find_shot(name):
    """Find shot matching the given name.

    Args:
        name (str): name to search for

    Returns:
        (TTShotRoot): matching shot
    """
    return get_single([
        _shot for _shot in find_shots() if _shot.name == name])


def find_shots(class_=None, filter_=None):
    """Find shots in the current job.

    Args:
        class_ (class): override shot root class
        filter_ (str): filter by shot name

    Returns:
        (TTShotRoot): list of shots
    """
    return sum([
        _seq.find_shots(class_=class_, filter_=filter_)
        for _seq in find_sequences()], [])
