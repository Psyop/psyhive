"""Tools for managing cacheable tank template representations."""

import collections

from psyhive.utils import store_result_on_obj

from psyhive.tk2.tk_templates import (
    TTSequenceRoot, TTRoot, TTStepRoot, TTWorkArea, TTWork, TTIncrement,
    TTOutputType, TTOutputName, TTOutputVersion, TTOutput, TTOutputFile,
    TTOutputFileSeq, find_sequences, find_asset_roots, get_work,
    cur_work)

_CACHEABLES = collections.defaultdict(dict)


class _CTTSequenceRoot(TTSequenceRoot):
    """Represents a sequence root dir with caching."""

    @store_result_on_obj
    def _read_shots(self, class_=None):
        """Find shots in this sequence.

        Args:
            class_ (class): override shot class

        Returns:
            (CTTRoot list): list of shots
        """
        _shots = super(_CTTSequenceRoot, self)._read_shots(class_=class_)
        return [obtain_cacheable(_shot) for _shot in _shots]


class _CTTRoot(TTRoot):
    """Represents a root dir with caching."""

    @store_result_on_obj
    def _read_step_roots(self, class_=None):
        """Find steps in this shot.

        Args:
            class_ (TTStepRoot): override step root class

        Returns:
            (CTTStepRoot list): list of steps
        """
        _roots = super(_CTTRoot, self)._read_step_roots(class_=class_)
        return [obtain_cacheable(_root) for _root in _roots]


class _CTTStepRoot(TTStepRoot):
    """Represents a step root dir with caching."""

    def get_work_area(self, dcc):
        """Get work area in this step for the given dcc.

        Args:
            dcc (str): dcc to get work area for

        Returns:
            (CTTWorkArea): work area
        """
        _work_area = super(_CTTStepRoot, self).get_work_area(dcc=dcc)
        return obtain_cacheable(_work_area)

    @store_result_on_obj
    def _read_output_types(self, class_=None):
        """Read output types in this step root from disk.

        Args:
            class_ (class): override output type class

        Returns:
            (CTTOutputType list): output type list
        """
        return [obtain_cacheable(_type)
                for _type in super(_CTTStepRoot, self)._read_output_types()]


class _CTTWorkArea(TTWorkArea):
    """Represents a work area dir with caching."""

    @store_result_on_obj
    def find_increments(self):
        """Find increments belonging to this work area.

        Returns:
            (CTTIncrement list): increment files
        """
        _incs = super(_CTTWorkArea, self).find_increments()
        return [obtain_cacheable(_inc) for _inc in _incs]

    @store_result_on_obj
    def find_work(self, class_=None):
        """Find work files inside this step root.

        Args:
            class_ (class): override work class

        Returns:
            (TTWork list): list of work files
        """
        _works = super(_CTTWorkArea, self).find_work(class_=class_)
        return [obtain_cacheable(_work) for _work in _works]

    @store_result_on_obj
    def get_metadata(self, verbose=0):
        """Read this work area's metadata yaml file.

        Args:
            verbose (int): print process data

        Returns:
            (dict): work area metadata
        """
        return super(_CTTWorkArea, self).get_metadata(verbose=verbose)


class _CTTWork(TTWork):
    """Represents a work file with caching."""

    @store_result_on_obj
    def get_metadata(self, data=None, catch=True, verbose=0):
        """Read this work area's metadata yaml file.

        Args:
            data (dict): override read data
            catch (bool): no error on work file missing from metadata
            verbose (int): print process data

        Returns:
            (dict): work area metadata
        """
        _work_area = self.get_work_area()
        return super(_CTTWork, self).get_metadata(
            data=data, catch=catch, verbose=verbose)

    @store_result_on_obj
    def get_work_area(self):
        """Get work area for this work file.

        Returns:
            (CTTWorkArea): work area
        """
        _area = super(_CTTWork, self).get_work_area()
        return obtain_cacheable(_area)

    @store_result_on_obj
    def get_step_root(self):
        """Get step root for this work file.

        Returns:
            (CTTStepRoot): step root
        """
        _root = super(_CTTWork, self).get_step_root()
        return obtain_cacheable(_root)


class _CTTIncrement(TTIncrement):
    """Represents a work increment file with caching."""


class _CTTOutputType(TTOutputType):
    """Represents an output type dir with caching."""

    @store_result_on_obj
    def _read_names(self, class_=None):
        """Read output names from dist.

        Args:
            class_ (class): override output name class

        Returns:
            (CTTOutputName list): list of output names
        """
        _names = super(_CTTOutputType, self)._read_names(class_=class_)
        return [obtain_cacheable(_name) for _name in _names]


class _CTTOutputName(TTOutputName):
    """Represents an output name dir with caching."""

    @store_result_on_obj
    def _read_versions(self, class_=None):
        """Read versions of this output name from disk.

        Args:
            class_ (class): override output version class

        Returns:
            (TTOutputVersion list): list of versions
        """
        _vers = super(_CTTOutputName, self)._read_versions(class_=class_)
        return [obtain_cacheable(_ver) for _ver in _vers]


class _CTTOutputVersion(TTOutputVersion):
    """Represents an output version dir with caching."""

    @store_result_on_obj
    def _read_outputs(self, class_=None):
        """Read outputs within this version dir from disk.

        Args:
            class_ (class): override output class

        Returns:
            (TTOutput list): list of outputs
        """
        _outs = super(_CTTOutputVersion, self)._read_outputs(class_=class_)
        return [obtain_cacheable(_out) for _out in _outs]


class _CTTOutput(TTOutput):
    """Represents an output dir with caching."""

    @store_result_on_obj
    def _read_files(self, verbose=0):
        """Read files/seqs within this output from disk.

        Args:
            verbose (int): print process data

        Returns:
            (TTOutputFile|TTOutputFileSeq list): output files/seqs
        """
        return [obtain_cacheable(_file)
                for _file in super(_CTTOutput, self)._read_files()]


class _CTTOutputFile(TTOutputFile):
    """Represents an output file with caching."""


class _CTTOutputFileSeq(TTOutputFileSeq):
    """Represents an output file seq with caching."""


def _map_class_to_cacheable(class_):
    """Get cacheable version of the given TT class.

    Args:
        class_ (class): class to convert

    Returns:
        (class): cacheable version of TT class
    """
    return {
        TTSequenceRoot: _CTTSequenceRoot,
        TTRoot: _CTTRoot,
        TTStepRoot: _CTTStepRoot,

        TTWorkArea: _CTTWorkArea,
        TTWork: _CTTWork,
        TTIncrement: _CTTIncrement,

        TTOutputType: _CTTOutputType,
        TTOutputName: _CTTOutputName,
        TTOutputVersion: _CTTOutputVersion,
        TTOutput: _CTTOutput,
        TTOutputFile: _CTTOutputFile,
        TTOutputFileSeq: _CTTOutputFileSeq,
    }[class_]


def clear_caches():
    """Clear all caches."""
    global _CACHEABLES
    _CACHEABLES = {}


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


def obtain_asset_roots():
    """Factory for asset roots in the current job.

    Returns:
        (CTTRoot): asset roots
    """
    return [obtain_cacheable(_root) for _root in find_asset_roots()]


def obtain_sequences():
    """Factory for sequence in the current job.

    Returns:
        (CTTSequenceRoot): sequences
    """
    return [obtain_cacheable(_seq) for _seq in find_sequences()]


def obtain_work(file_):
    """Factory for work file objects.

    Args:
        file_ (str): path to obtain work object for

    Returns:
        (CTTWorkFile): work file
    """
    _work = get_work(file_)
    if not _work:
        return None
    return obtain_cacheable(_work)


def obtain_cur_work():
    """Factory for current work file object.

    Returns:
        (CTTWorkFile): current work file
    """
    _cur_work = cur_work()
    if not _cur_work:
        return None
    return obtain_cacheable(_cur_work)
