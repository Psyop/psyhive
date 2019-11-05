"""Tools for providing tank template shot objects with built in caching.

The objects are all accessed via factory pattern style obtain functions.
"""

import copy

from psyhive import host
from psyhive.utils import (
    Cacheable, store_result_on_obj, find,
    lprint, dprint, store_result_content_dependent, Seq)

from psyhive.tk.templates.base import (
    TTWorkFileBase, TTWorkAreaBase, TTOutputNameBase, TTStepRootBase)
from psyhive.tk.templates.assets import (
    TTMayaAssetWork, TTAssetWorkAreaMaya, TTAssetOutputFile,
    TTAssetOutputVersion, TTAssetOutputName, TTAssetStepRoot)
from psyhive.tk.templates.shots import (
    TTMayaShotWork, TTShotWorkAreaMaya, TTShotRoot, TTShotStepRoot,
    TTShotOutputName, TTShotOutputVersion, TTNukeShotWork)
from psyhive.tk.templates.tools import get_work
from psyhive.tk.templates.misc import get_template

_CACHEABLES = {}
_WORK_FILES = {}
_WORK_AREAS = {}


def clear_caches():
    """Clear all caches."""
    global _WORK_FILES, _WORK_AREAS, _CACHEABLES
    _CACHEABLES = {}
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

        tk.TTAssetOutputFile: _CTTAssetOutputFile,
        tk.TTAssetOutputName: _CTTAssetOutputName,
        tk.TTAssetOutputVersion: _CTTAssetOutputVersion,
        tk.TTAssetStepRoot: _CTTAssetStepRoot,
        tk.TTAssetWorkAreaMaya: _CTTAssetWorkAreaMaya,

        tk.TTShotOutputName: _CTTShotOutputName,
        tk.TTShotOutputVersion: _CTTShotOutputVersion,
        tk.TTShotRoot: _CTTShotRoot,
        tk.TTShotStepRoot: _CTTShotStepRoot,
        tk.TTShotWorkAreaMaya: _CTTShotWorkAreaMaya,

        tk.TTMayaAssetWork: _CTTMayaAssetWork,
        tk.TTMayaShotWork: _CTTMayaShotWork,
        tk.TTNukeShotWork: _CTTNukeShotWork,

    }[class_]


def obtain_cur_work():
    """Get cacheable version of the current work file.

    Returns:
        (_CTTWorkFileBase): work file
    """
    _scene = host.cur_scene()
    if not _scene:
        return None
    return obtain_work(_scene)


def obtain_cacheable(source):
    """Factory for any cachable object.

    This maps any existing tank template object to its cacheable version,
    making sure that only one instance of each cacheable object exists.

    Args:
        source (TTBase): source tank template object
    """
    global _CACHEABLES
    _type = _map_class_to_cacheable(source.__class__)
    if _type not in _CACHEABLES:
        _CACHEABLES[_type] = {}
    if source not in _CACHEABLES[_type]:
        _cacheable = _type(source.path)
        _CACHEABLES[_type][source] = _cacheable
    return _CACHEABLES[_type][source]


def obtain_work(file_, catch=False):
    """Factory for cacheable work file object.

    Args:
        file_ (str): path to work file
        catch (bool): no error if file fails to map to work

    Returns:
        (_CTTWorkFileBase): cacheable work file
    """
    global _WORK_FILES
    _work = get_work(file_, catch=catch)
    if not _work:
        return None
    if _work not in _WORK_FILES:
        _type = _map_class_to_cacheable(_work.__class__)
        _WORK_FILES[_work] = _type(_work.path)
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
        _type = _map_class_to_cacheable(work_area.__class__)
        _WORK_AREAS[work_area] = _type(work_area.path)
    return _WORK_AREAS[work_area]


class _CTTAssetOutputFile(TTAssetOutputFile):
    """Cacheable TTAssetOutputFile object."""


class _CTTShotRoot(TTShotRoot):
    """Cacheable TTShotRoot object."""

    @store_result_on_obj
    def find_step_roots(self, class_=None, filter_=None):
        """Find step roots.

        Args:
            class_ (type): not implemented
            filter_ (str): not implemented

        Returns:
            (_CTTShotStepRoot list): list of step roots
        """
        assert not class_
        assert not filter_
        return [
            obtain_cacheable(_step)
            for _step in super(_CTTShotRoot, self).find_step_roots()]


class _CTTStepRootBase(object):
    """Base class for any cacheable step root."""

    @store_result_on_obj
    def read_output_names(self, verbose=0):
        """Find output names.

        Args:
            verbose (int): print process data

        Returns:
            (_CTTShotOutputName list): output names
        """
        _names = TTStepRootBase.read_output_names(self, verbose=verbose)
        return [obtain_cacheable(_name) for _name in _names]


class _CTTAssetStepRoot(_CTTStepRootBase, TTAssetStepRoot):
    """Cacheable TTShotStepRoot object."""


class _CTTShotStepRoot(_CTTStepRootBase, TTShotStepRoot):
    """Cacheable TTShotStepRoot object."""


class _CTTOutputNameBase(object):
    """Base class for any cacheable output name."""

    @store_result_on_obj
    def find_vers(self, catch=False):
        """Find versions.

        Args:
            catch (bool): no error if no versions found

        Returns:
            (TTShotOutputVersion list): versions
        """
        _vers = TTOutputNameBase.find_vers(self, catch=catch)
        return [obtain_cacheable(_ver) for _ver in _vers]


class _CTTAssetOutputName(_CTTOutputNameBase, TTAssetOutputName):
    """Cacheable TTAssetOutputName object."""


class _CTTShotOutputName(_CTTOutputNameBase, TTShotOutputName):
    """Cacheable TTShotOutputName object."""


class _CTTAssetOutputVersion(TTAssetOutputVersion):
    """Cacheable asset output version."""

    @store_result_on_obj
    def find_work_file(self, verbose=0):
        """Find work file associated with this version.

        Args:
            verbose (int): print process data

        Returns:
            (_CTTWorkFileBase|None): work file (if any)
        """
        _work = super(_CTTAssetOutputVersion, self).find_work_file(
            verbose=verbose)
        if _work:
            _work = obtain_cacheable(_work)
        return _work

    @store_result_on_obj
    def _read_outputs(self, verbose=0):
        """Read outputs in this version.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputBase list): outputs
        """
        return super(_CTTAssetOutputVersion, self)._read_outputs(
            verbose=verbose)


class _CTTShotOutputVersion(TTShotOutputVersion):
    """Cacheable shot output version."""

    @store_result_on_obj
    def find_work_file(self, verbose=0):
        """Find work file associated with this version.

        Args:
            verbose (int): print process data

        Returns:
            (_CTTWorkFileBase|None): work file (if any)
        """
        _work = super(_CTTShotOutputVersion, self).find_work_file(
            verbose=verbose)
        if _work:
            _work = obtain_cacheable(_work)
        return _work

    @store_result_on_obj
    def _read_outputs(self, verbose=0):
        """Read outputs in this version.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputBase list): outputs
        """
        return super(_CTTShotOutputVersion, self)._read_outputs(
            verbose=verbose)


class _CTTWorkAreaBase(object):
    """Base class for any work area object."""

    data = None
    maya_work_type = None
    maya_inc_type = None
    path = None

    @store_result_on_obj
    def find_increments(self, force=False):
        """Find increments belonging to this work area.

        Args:
            force (bool): force reread increment files

        Returns:
            (TTWorkIncrementBase list): increment files
        """
        return TTWorkAreaBase.find_increments(self)

    @store_result_on_obj
    def find_work(self, force=False, verbose=1):
        """Find work files within this work area.

        Args:
            force (bool): force reread work files from disk
            verbose (int): print process data

        Returns:
            (_CTTWorkFileBase): list of cachable work files
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


class _CTTAssetWorkAreaMaya(TTAssetWorkAreaMaya, _CTTWorkAreaBase):
    """Cachable asset work area for maya."""

    @store_result_on_obj
    def get_metadata(self, force=False, **kwargs):
        """Get metadata for this work area.

        Args:
            force (bool): force reread from disk

        Returns:
            (dict): metadata
        """
        return super(_CTTAssetWorkAreaMaya, self).get_metadata(**kwargs)


class _CTTShotWorkAreaMaya(TTShotWorkAreaMaya, _CTTWorkAreaBase):
    """Cachable shot work area for maya."""

    @store_result_on_obj
    def get_metadata(self, force=False, **kwargs):
        """Get metadata for this work area.

        Args:
            force (bool): force reread from disk

        Returns:
            (dict): metadata
        """
        return super(_CTTShotWorkAreaMaya, self).get_metadata(**kwargs)


class _CTTWorkFileBase(Cacheable):
    """Base class for any maya work file."""

    @property
    def cache_fmt(self):
        """Get cache format.

        Returns:
            (str): format for cache files
        """
        return '{}/cache/psyhive/{}_{{}}.cache'.format(
            self.get_work_area().path, self.basename)

    def find_captures(self):
        """Find captures generated from this work file.

        Returns:
            (TTOutputFileSeqBase list): list of captures
        """
        return [
            _output for _output in self.find_seqs()
            if _output.output_type == 'capture']

    def find_caches(self):
        """Find caches generated from this work file.

        Returns:
            (TTOutputFileBase list): list of caches
        """
        return [
            _output for _output in self.find_outputs()
            if _output.output_type in ['animcache', 'camcache']]

    @store_result_on_obj
    def find_increments(self, force=False):
        """Find increments of this work file.

        Args:
            force (bool): force reread increments from disk

        Returns:
            (TTWorkIncrementBase list): list of incs
        """
        return TTWorkFileBase.find_increments(self)

    @store_result_on_obj
    def find_latest(self, vers=None):
        """Find latest version of this work file.

        Args:
            vers (TTWorkFileBase list): override list of work files

        Returns:
            (TTWorkFileBase): latest work file
        """
        _latest = super(_CTTWorkFileBase, self).find_latest(vers=vers)
        if _latest:
            return obtain_work(_latest.path)
        return None

    def find_publishes(self):
        """Find publishes generated from this work file.

        Returns:
            (TTOutputFileBase list): list of publishes
        """
        return [
            _output for _output in self.find_outputs()
            if _output.output_type in ['rig', 'shadegeo', 'geometry']]

    def find_renders(self):
        """Find renders generated from this work file.

        Returns:
            (TTOutputFileSeqBase list): list of render
        """
        return [
            _output for _output in self.find_seqs()
            if not _output.output_type == 'capture']

    def find_seqs(self):
        """Find all file sequences generated from this work file.

        Returns:
            (TTOutputFileSeqBase list): list of seqs
        """
        return [
            _output for _output in self.find_outputs()
            if isinstance(_output, Seq)]

    @store_result_on_obj
    def get_metadata(self, data=None, force=False, verbose=0):
        """Get metadata for this workfile.

        Args:
            data (dict): pass metadata to avoid disk read
            force (bool): force reread data
            verbose (int): print process data

        Returns:
            (dict): work file metadata
        """
        _work_area = self.get_work_area()
        _data = data or _work_area.get_metadata(force=force)
        return super(_CTTWorkFileBase, self).get_metadata(
            data=data, verbose=verbose)

    @store_result_on_obj
    def get_work_area(self):
        """Get work area associated with this work file.

        Returns:
            (_CTTWorkAreaBase): cachable work area
        """
        _work_area = super(_CTTWorkFileBase, self).get_work_area()
        return obtain_work_area(_work_area)

    def set_comment(self, comment):
        """Set comment for this work file.

        Args:
            comment (str): comment to apply
        """
        from psyhive import tk
        # Don't use super as this class is not TTWorkFileBase instance
        tk.TTWorkFileBase.set_comment(self, comment)
        self.get_metadata(force=True)


class _CTTMayaAssetWork(_CTTWorkFileBase, TTMayaAssetWork):
    """Asset work file with built in caching."""

    @store_result_content_dependent
    def find_outputs(self, force=False, **kwargs):
        """Find outputs generated from this work file.

        Args:
            force (bool): force reread from disk

        Returns:
            (list): list of outputs
        """
        return super(_CTTMayaAssetWork, self).find_outputs(**kwargs)


class _CTTMayaShotWork(_CTTWorkFileBase, TTMayaShotWork):
    """Shot work file with built in caching."""

    @store_result_content_dependent
    def find_outputs(self, force=False, **kwargs):
        """Find outputs generated from this work file.

        Args:
            force (bool): force reread from disk

        Returns:
            (list): list of outputs
        """
        return super(_CTTMayaShotWork, self).find_outputs(**kwargs)


class _CTTNukeShotWork(_CTTWorkFileBase, TTNukeShotWork):
    """Shot work file with built in caching."""

    @store_result_content_dependent
    def find_outputs(self, force=False, **kwargs):
        """Find outputs generated from this work file.

        Args:
            force (bool): force reread from disk

        Returns:
            (list): list of outputs
        """
        return super(_CTTNukeShotWork, self).find_outputs(**kwargs)
