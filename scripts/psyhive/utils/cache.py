"""Tools for managing the caching of data."""

import cPickle
import functools
import inspect
import operator
import os
import tempfile
import time

import six

from .filter_ import passes_filter
from .misc import lprint, dprint


class Cacheable(object):
    """Base class for any cacheable object."""
    cache_fmt = None

    def cache_read(self, tag):
        """Read cached data from the given tag.

        Args:
            tag (str): data tag to read

        Returns:
            (any): cached data
        """
        _file = self.cache_fmt.format(tag)
        try:
            return obj_read(file_=_file)
        except OSError:
            return None

    def cache_write(self, tag, data, verbose=0):
        """Write data to the given cache.

        Args:
            tag (str): tag to store data to
            data (any): data to store
            verbose (int): print process data
        """
        _file = self.cache_fmt.format(tag)
        obj_write(file_=_file, obj=data, verbose=verbose)


class CacheMissing(OSError):
    """Raise when a cache doesn't exist."""


class ReadError(RuntimeError):
    """Raised on failed to read cached object."""


class WriteError(RuntimeError):
    """Raised on fail to write cached object."""


def build_cache_fmt(path, namespace='psyhive'):
    """Build cache format string for the given namespace.

    This maps the path to a location in tmp dir.

    Args:
        path (str): path of cacheable
        namespace (str): namespace for cache

    Returns:
        (str): cache format path
    """
    from .path import Path, abs_path
    _path = Path(path)

    return abs_path(
        '{tmp}/{namespace}/cache/{dir}/{base}_{{}}.cache'.format(
            tmp=tempfile.gettempdir(),
            dir=_path.dir.replace(':', ''),
            base=_path.basename,
            namespace=namespace))


def _depend_path_makes_cache_outdated(
        cache_file, depend_path, cache_file_exists=None, verbose=0):
    """Check of a depend path makes a cache outdated.

    Args:
        cache_file (str): path to cache file
        depend_path (str): path to depend path
        cache_file_exists (bool): whether cache file exists
        verbose (int): print process data
    """
    if not depend_path:
        return False

    # Check if cache file exists
    if cache_file_exists is None:
        _cache_file_exists = os.path.exists(cache_file)
    else:
        _cache_file_exists = cache_file_exists
    if not _cache_file_exists:
        return False

    if verbose:
        print ' - DEPEND PATH', os.path.exists(depend_path), depend_path

    return (
        os.path.exists(depend_path) and
        os.path.getmtime(depend_path) > os.path.getmtime(cache_file))


def get_result_storer(
        key=None, timeout=None, ignore_args=False, id_as_key=False,
        get_depend_var=None, args_filter=None, get_depend_path=None,
        verbose=0):
    """Build a decorator to store the result of a function.

    By default, the result is regenerated for each combination of args. If
    any combination of args is applied to the function more than once,
    the result from the initial execution of the function is used.

    Args:
        key (str): arg to use as a key (ie. ignore other arg values)
        timeout (float): cause the cached result to expire after this
            many seconds
        ignore_args (bool): ignore all args (always return the same result)
        id_as_key (bool): use only the id of the first arg as the
            results key
        get_depend_var (fn): function to read a depend variable - if this
            variable changes value then the cached data is discarded
        args_filter (str): string filter to apply to args list
        get_depend_path (fn): function to get a path - if the mtime of
            this path is greater than the time at which the cache was
            generated then the cache is regenerated
        verbose (int): print process data
    """

    def _store_result(func):

        # Dicts are used for _depend_var/_read_time to avoid global errors
        _depend_var = {None: get_depend_var()} if get_depend_var else None
        _read_time = {}
        _result_cache = {}
        _arg_spec = inspect.getargspec(func)
        dprint('Reset results cache', func.__name__, verbose=verbose)

        def _depend_path_forces_recache(args, read_time):

            if not get_depend_path:
                return False
            if not read_time:
                return False

            _obj = args[0]
            _path = get_depend_path(_obj)
            _mtime = os.path.getmtime(_path)
            _force_recache = _mtime > read_time

            return _force_recache

        def _depend_var_forces_recache():
            if not get_depend_var:
                return False
            _current_depend_var = get_depend_var()
            _result = _current_depend_var != _depend_var[None]
            _depend_var[None] = _current_depend_var
            return _result

        def _timeout_forces_recache():
            return timeout is not None and (
                not _read_time or time.time() - _read_time[None] > timeout)

        @functools.wraps(func)
        def _fn_wrapper(*args, **kwargs):

            dprint('Executing', func.__name__, verbose=verbose)

            # Catch bad kwarg provided
            for _kwarg in kwargs:
                if _kwarg not in _arg_spec.args:
                    lprint(' - args spec', _arg_spec.args, verbose=verbose)
                    raise TypeError(
                        "{}() got an unexpected keyword argument '{}'".format(
                            func.__name__, _kwarg))

            # Get a full list of kwargs
            _args_key = []
            _args_dict = {}
            for _idx, _arg_name in enumerate(_arg_spec.args):
                _arg_idx = _idx-len(_arg_spec.args)
                if _arg_name in ['force', 'verbose']:
                    continue
                elif args_filter and not passes_filter(_arg_name, args_filter):
                    continue
                elif _idx < len(args):
                    _val = args[_idx]
                elif _arg_name in kwargs:
                    _val = kwargs[_arg_name]
                elif abs(_arg_idx) > len(_arg_spec.defaults):
                    raise TypeError(
                        'It looks like some of the required args are '
                        'missing {}'.format(func.__name__))
                else:
                    _val = _arg_spec.defaults[_arg_idx]
                _args_key.append((_arg_name, _val))
                _args_dict[_arg_name] = _val

            # Get key to reference this result
            if id_as_key:
                _key = id(args[0]), args[0]
            elif ignore_args:
                _key = None
            elif key:
                _key = _args_dict[key]
            else:
                _key = tuple(_args_key)
                for _name, _val in _key:
                    if isinstance(_val, dict):
                        raise RuntimeError("Cacher applied to dict arg")
            del _args_key
            lprint(' - args key', _key, verbose=verbose)
            lprint(' - results keys', _result_cache.keys(), verbose=verbose)

            # Calculate result if needed
            if (
                    kwargs.get('force') or
                    _key not in _result_cache or
                    _timeout_forces_recache() or
                    _depend_var_forces_recache() or
                    _depend_path_forces_recache(args, _read_time.get(None))):

                # Store result
                _result = func(*args, **kwargs)
                _result_cache[_key] = _result

                # Store read time
                _read_time[None] = time.time()

            lprint(
                ' - results keys (final)', _result_cache.keys(),
                verbose=verbose)
            return _result_cache[_key]

        return _fn_wrapper

    return _store_result


def get_result_to_file_storer(
        get_depend_path=None, min_mtime=None, create_dir=True,
        max_age=None, allow_fail=True, verbose=0):
    """Build a decorator that stores the result of a function to a file.

    Args:
        get_depend_path (fn): function to get a path - if the mtime of
            this path is greater than the time at which the cache was
            generated then the cache is regenerated
        min_mtime (float): if the cache was generated before this time
            then it should be ignored
        create_dir (bool): create the dir of the cache file if it
            doesn't exist
        max_age (float): if the age of the cache (in secs) is more than
            this value then it should be ignored (ie. regenerated)
        allow_fail (bool): error if cache fails to write to disk
        verbose (int): print process data
    """

    def _store_result_to_file(method):

        @get_result_storer(key='key')
        def _get_result(
                key, cache_file, args, kwargs, force=False,
                cache_file_exists=None):

            # Try and read from file
            if not force and cache_file:
                if cache_file_exists is None:
                    _cache_file_exists = os.path.exists(cache_file)
                else:
                    _cache_file_exists = cache_file_exists
                if not _cache_file_exists:
                    pass
                else:
                    try:
                        return obj_read(cache_file)
                    except ReadError:
                        pass

            # Calculate result
            lprint(' - CALCULATING RESULT', verbose=verbose)
            _result = method(*args, **kwargs)

            # Write to file
            try:
                obj_write(
                    _result, file_=cache_file, create_dir=create_dir,
                    verbose=max(verbose-1, 0))
            except (OSError, IOError) as _exc:
                if not allow_fail:
                    raise _exc

            return _result

        @functools.wraps(method)
        def _result_writer(*args, **kwargs):

            from .path import abs_path

            dprint('READING RESULT', method.__name__, verbose=verbose)

            # Read object/key/force
            _obj = args[0]
            _key = _obj, id(_obj), method.__name__
            _force = kwargs.get('force')

            # Get cache file path
            if _obj.cache_fmt:
                try:
                    _cache_file = abs_path(
                        _obj.cache_fmt.format(method.__name__))
                except TypeError:
                    raise TypeError(
                        'Bad cache file fmt {}'.format(_obj.cache_fmt))
            else:
                _cache_file = None
            _cache_file_exists = None
            lprint(' - READ CACHE FILE', _cache_file, verbose=verbose)

            # Read depend path
            if not _force and _cache_file and get_depend_path:
                _depend_path = get_depend_path(_obj)
                _cache_file_exists = os.path.exists(_cache_file)
                if _depend_path_makes_cache_outdated(
                        cache_file=_cache_file, depend_path=_depend_path,
                        cache_file_exists=_cache_file_exists,
                        verbose=verbose):
                    lprint(' - DEPEND PATH OUTDATED CACHE', verbose=verbose)
                    _force = True
                else:
                    lprint(
                        ' - DEPEND PATH DID NOT OUTDATE CACHE',
                        verbose=verbose)

            # Apply age/mtime constraints
            if not _force and _cache_file and (min_mtime or max_age):
                if _cache_file_exists is None:
                    _cache_file_exists = os.path.exists(_cache_file)
                if _cache_file_exists:
                    _mtime = os.path.getmtime(_cache_file)
                    _age = time.time() - _mtime
                    if min_mtime and _mtime < min_mtime:
                        _force = True
                    elif max_age and _age > max_age:
                        _force = True

            return _get_result(
                key=_key, args=args, kwargs=kwargs, force=_force,
                cache_file=_cache_file, cache_file_exists=_cache_file_exists)

        return _result_writer

    return _store_result_to_file


def obj_read(file_, verbose=0):
    """Read a python object from file.

    Args:
        file_ (str): path to read
        verbose (int): print process data
    """
    from .path import abs_path

    assert isinstance(file_, six.string_types)
    _path = abs_path(file_)
    if not os.path.exists(_path):
        raise OSError("Path is missing {}".format(_path))

    _file = open(_path, "r")
    try:
        _obj = cPickle.load(_file)
    except Exception as _exc:
        lprint(_exc, verbose=verbose)
        raise ReadError(_path)
    _file.close()

    return _obj


def obj_write(obj, file_, create_dir=True, verbose=0):
    """Write a python object to file.

    Args:
        obj (any): object to write
        file_ (str): path to write object to
        create_dir (bool): create the parent dir if it doesn't exist
        verbose (int): print process data
    """
    from .path import abs_path, test_path

    _path = abs_path(file_)
    lprint('WRITING TO', _path, verbose=verbose)

    if create_dir:
        test_path(os.path.dirname(_path))

    _file = open(_path, "w")
    cPickle.dump(obj, _file)
    _file.close()

    return _path


def store_result(func):
    """Decorator to store the result of a function.

    Args:
        func (fn): function to store result of
    """
    return get_result_storer()(func)


def store_result_on_obj(method):
    """Decorator which stores the result of a method on the object.

    This generates a unique result for each instance of the object. This
    cache acts like a property (except it is still a function).

    Args:
        method (fn): method to decorate

    Returns:
        (fn): decorated function
    """
    return get_result_storer(id_as_key=True)(method)


def store_result_content_dependent(method):
    """Decorator to save result of a scene file analysis.

    The result expires if the mtime of the scene file is higher than
    the cache generation time.

    Args:
        method (fn): method to decorate

    Returns:
        (fn): decorated function
    """
    return get_result_to_file_storer(
        get_depend_path=operator.attrgetter('path'))(method)


def store_result_to_file(method):
    """Decorator to the result of a method to a file.

    This must be applied to an object which inherits from Cachable. The
    path to the cache file is reads from the obj.cache_fmt attribute.
    This str should contain a {} format placeholder which will be
    replaced with the method name to give the cache file path.

    Args:
        method (fn): method to decorate

    Returns:
        (fn): decorated method
    """
    return get_result_to_file_storer()(method)
