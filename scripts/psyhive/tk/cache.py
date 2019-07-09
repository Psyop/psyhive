"""Tools for providing tank template shot objects with built in caching.

The objects are all accessed via factory pattern style obtain functions.
"""

import copy

from psyhive.utils import (
    Cacheable, store_result_to_file, store_result_on_obj, find,
    lprint, dprint)

from psyhive.tk.templates.assets import TTMayaAssetWork, TTAssetWorkAreaMaya
from psyhive.tk.templates.shots import TTMayaShotWork, TTShotWorkAreaMaya
from psyhive.tk.templates.tools import get_work
from psyhive.tk.templates.misc import get_template

_WORK_FILES = {}
_WORK_AREAS = {}


def clear_caches():
    """Clear all caches."""
    global _WORK_FILES, _WORK_AREAS
    _WORK_FILES = {}
    _WORK_AREAS = {}


def _map_class_to_cacheable(class_):
    """Get cacheable version of the given tk template class.

    Args:
        class_ (TTBase): tank template class

    Returns:
        (CTT file): cacheable version
    """
    from psyhive import tk
    return {
        tk.TTAssetWorkAreaMaya: _CTTAssetWorkAreaMaya,
        tk.TTShotWorkAreaMaya: _CTTShotWorkAreaMaya,
        tk.TTMayaAssetWork: _CTTMayaAssetWork,
        tk.TTMayaShotWork: _CTTMayaShotWork,
    }[class_]


def obtain_work(file_):
    """Factory for cacheable work file object.

    Args:
        file_ (str): path to work file

    Returns:
        (_CTTMayaWorkBase): cacheable work file
    """
    global _WORK_FILES
    _work = get_work(file_, catch=False)
    if _work not in _WORK_FILES:
        _work_type = _map_class_to_cacheable(_work.__class__)
        _WORK_FILES[_work] = _work_type(_work.path)
    return _WORK_FILES[_work]


def obtain_work_area(work_area):
    """Factory for work area objects.

    Args:
        work_area (TTWorkAreaBase): work area

    Returns:
        (_CTTWorkAreaBase): cacheable work area
    """
    global _WORK_AREAS
    if work_area not in _WORK_AREAS:
        _work_area_type = _map_class_to_cacheable(work_area.__class__)
        _WORK_AREAS[work_area] = _work_area_type(work_area.path)
    return _WORK_AREAS[work_area]


class _CTTWorkAreaBase(object):
    """Base class for any work area object."""

    data = None
    maya_work_type = None
    path = None

    @store_result_on_obj
    def find_work(self, force=False, verbose=1):
        """Find work files within this work area.

        Args:
            force (bool): force reread work files from disk
            verbose (int): print process data

        Returns:
            (_CTTMayaWorkBase): list of cachable work files
        """
        dprint('FINDING WORK', self.path, verbose=verbose)

        # Get work dir
        _tmpl = get_template(self.maya_work_type.hint)
        _data = copy.copy(self.data)
        _data['Task'] = 'blah'
        _data['extension'] = 'mb'
        _data['version'] = 1
        _tmp_path = _tmpl.apply_fields(_data)
        _tmp_work = self.maya_work_type(_tmp_path)

        # Find work files + make cachable
        _works = []
        for _file in find(_tmp_work.dir, depth=1, type_='f'):
            try:
                _tmp_work = self.maya_work_type(_file)
            except ValueError:
                continue
            lprint(' - ADDING', _file, verbose=verbose > 1)
            _work = obtain_work(_tmp_work.path)
            _works.append(_work)
        return _works

    @store_result_on_obj
    def get_metadata(self, force=False, **kwargs):
        """Read and store the metadata.

        Args:
            force (bool): force reread metadata from disk

        Returns:
            (dict): work area metadata
        """
        return super(_CTTWorkAreaBase, self).get_metadata(**kwargs)


class _CTTAssetWorkAreaMaya(TTAssetWorkAreaMaya, _CTTWorkAreaBase):
    """Cachable asset work area for maya."""


class _CTTShotWorkAreaMaya(TTShotWorkAreaMaya, _CTTWorkAreaBase):
    """Cachable shot work area for maya."""


class _CTTMayaWorkBase(Cacheable):
    """Base class for any maya work file."""

    @property
    def cache_fmt(self):
        """Get cache format.

        Returns:
            (str): format for cache files
        """
        return '{}/cache/psyhive/{}_{{}}.cache'.format(
            self.get_work_area().path, self.basename)

    @store_result_on_obj
    def get_metadata(self, data, force=False):
        """Get metadata for this workfile.

        Args:
            data (dict): pass metadata to avoid disk read
            force (bool): force reread data

        Returns:
            (dict): work file metadata
        """
        _data = data or self.get_work_area().get_metadata(force=force)
        return super(_CTTMayaWorkBase, self).get_metadata(data=data)

    @store_result_on_obj
    def get_work_area(self):
        """Get work area associated with this work file.

        Returns:
            (_CTTWorkAreaBase): cachable work area
        """
        _work_area = super(_CTTMayaWorkBase, self).get_work_area()
        return obtain_work_area(_work_area)

    def find_captures(self):
        """Find captures generated from this work file.

        Returns:
            (TTOutputFileSeqBase list): list of captures
        """
        return [
            _output for _output in self.find_outputs()
            if _output.output_type == 'capture']

    def find_publishes(self):
        """Find publishes generated from this work file.

        Returns:
            (TTOutputFileBase list): list of publishes
        """
        return [
            _output for _output in self.find_outputs()
            if _output.output_type in ['rig', 'shadegeo']]


class _CTTMayaAssetWork(_CTTMayaWorkBase, TTMayaAssetWork):
    """Asset work file with built in caching."""

    @store_result_to_file
    def find_outputs(self, force=False, **kwargs):
        """Find outputs generated from this work file.

        Args:
            force (bool): force reread from disk

        Returns:
            (list): list of outputs
        """
        return super(_CTTMayaAssetWork, self).find_outputs(**kwargs)


class _CTTMayaShotWork(_CTTMayaWorkBase, TTMayaShotWork):
    """Shot work file with built in caching."""

    @store_result_to_file
    def find_outputs(self, force=False, **kwargs):
        """Find outputs generated from this work file.

        Args:
            force (bool): force reread from disk

        Returns:
            (list): list of outputs
        """
        return super(_CTTMayaShotWork, self).find_outputs(**kwargs)
