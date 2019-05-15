"""Tools relating to tank templates within shots."""

from tank.platform import current_engine

from psyhive import pipe
from psyhive.utils import find

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


class TTShotRoot(TTRootBase):
    """Represents a tank template shot root."""

    hint = 'shot_root'

    @property
    def step_type(self):
        """Get step type."""
        return TTShotStepRoot


class TTShotStepRoot(TTStepRootBase, _TTShotChildBase):
    """Represents a tank template shot step root."""

    hint = 'shot_step_root'
    work_area_maya_hint = 'shot_work_area_maya'

    @property
    def work_area_maya_type(self):
        """Get work area type."""
        return TTShotWorkAreaMaya


class TTShotWorkAreaMaya(TTWorkAreaBase, _TTShotChildBase):
    """Represents a tank template shot work area for maya."""

    hint = 'shot_work_area_maya'


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


def find_shots():
    """Find shots in the current job.

    Returns:
        (TTShotRoot): list of shots
    """
    _seq_path = pipe.cur_project().path+'/sequences'
    _shots = []
    for _path in find(_seq_path, depth=2):
        try:
            _shot = TTShotRoot(_path)
        except ValueError:
            continue
        _shots.append(_shot)
    return _shots
