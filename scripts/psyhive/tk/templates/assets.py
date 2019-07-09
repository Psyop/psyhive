"""Tools for mananging asset type tank templates."""

import copy

from psyhive import pipe
from psyhive.utils import find

from psyhive.tk.templates.base import (
    TTBase, TTWorkAreaBase, TTWorkFileBase, TTOutputVerBase,
    TTRootBase, TTStepRootBase, TTDirBase, TTOutputFileSeqBase)


class _TTAssetCpntBase(object):
    """Base class for any asset component tank template."""

    work_area_maya_hint = 'asset_work_area_maya'

    @property
    def maya_work_type(self):
        """Get work area type for maya."""
        return TTMayaAssetWork

    @property
    def output_root_type(self):
        """Get output root type."""
        return TTAssetOutputRoot

    @property
    def output_name_type(self):
        """Get output name type."""
        return TTAssetOutputName

    @property
    def output_version_type(self):
        """Get output version type."""
        return TTAssetOutputVersion

    @property
    def output_file_type(self):
        """Get output file type."""
        return TTAssetOutputFile

    @property
    def output_file_seq_type(self):
        """Get output file seq type."""
        return TTAssetOutputFileSeq

    @property
    def step_root_type(self):
        """Get step root type."""
        return TTAssetStepRoot

    @property
    def work_area_maya_type(self):
        """Get work area type for maya."""
        return TTAssetWorkAreaMaya


class TTAssetRoot(_TTAssetCpntBase, TTRootBase):
    """Represents a tank asset root."""

    hint = 'asset_root'
    shot = None


class TTAssetStepRoot(_TTAssetCpntBase, TTStepRootBase):
    """Represents a tank asset step root."""

    hint = 'asset_step_root'


class TTAssetWorkAreaMaya(TTWorkAreaBase, _TTAssetCpntBase):
    """Represents a tank asset work area for maya."""

    hint = 'asset_work_area_maya'


class TTMayaAssetWork(_TTAssetCpntBase, TTWorkFileBase):
    """Represents a tank asset work file for maya."""

    hint = 'maya_asset_work'
    shot = None
    work_area_type = TTAssetWorkAreaMaya


class TTMayaAssetIncrement(TTWorkFileBase):
    """Represents a tank asset work file for maya."""

    hint = 'maya_asset_increment'


class TTAssetOutputRoot(TTDirBase):
    """Represents a tank asset output name."""

    hint = 'asset_output_root'


class TTAssetOutputName(TTDirBase):
    """Represents a tank asset output name."""

    hint = 'asset_output_name'


class TTAssetOutputVersion(TTOutputVerBase):
    """Represents an tank asset output version."""

    asset = None
    hint = 'asset_output_version'
    sg_asset_type = None

    def get_display_tags(self):
        """Get display tags for this version.

        Returns:
            (tuple): display data
        """
        return (
            self.sg_asset_type, self.step, self.task, self.asset,
            self.get_status())

    def get_name(self):
        """Get parent asset output name object.

        Returns:
            (TTAssetOutputName): parent output name
        """
        return TTAssetOutputName(self.path)


class TTAssetOutputFile(TTBase):
    """Represents an tank asset output file."""

    hint = 'asset_output_file'
    sg_asset_type = None
    version = None

    def get_latest(self):
        """Get latest version asset stream.

        Returns:
            (TTAssetOutputFile): latest asset output file
        """
        _ver = TTAssetOutputVersion(self.path)
        _latest = _ver.find_latest()
        _data = copy.copy(self.data)
        _data['version'] = _latest.version
        return TTAssetOutputFile(self.tmpl.apply_fields(_data))

    def is_latest(self):
        """Check if this is the latest version.

        Returns:
            (bool): latest status
        """
        return self.get_latest() == self


class TTAssetOutputFileSeq(TTOutputFileSeqBase, _TTAssetCpntBase):
    """Represents a asset output file seq tank template path."""

    hint = 'asset_output_file_seq'


def find_asset_roots():
    """Read asset roots."""
    _root = pipe.cur_project().path+'/assets'
    _roots = []
    for _dir in find(_root, depth=3, type_='d'):
        try:
            _asset = TTAssetRoot(_dir)
        except ValueError:
            continue
        _roots.append(_asset)

    return _roots
