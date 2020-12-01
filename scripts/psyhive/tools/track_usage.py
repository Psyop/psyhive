"""Tools for tracking tool usage using kibana."""

import datetime
import functools
import getpass
import os
import pprint
import platform
import sys
import time

import six

from psyhive import host, pipe
from psyhive.utils import dprint, dev_mode, File, abs_path, lprint

_ELASTIC_URL = 'http://la1dock001.psyop.tv:9200'
_ES_DATA_TYPE = 'data'
_INDEX_MAPPING = {
    'mappings': {
        _ES_DATA_TYPE: {
            'properties': {
                'args': {'type': 'string', 'index': 'not_analyzed'},
                'cwd': {'type': 'string', 'index': 'not_analyzed'},
                'filename': {'type': 'string', 'index': 'not_analyzed'},
                'function': {'type': 'string', 'index': 'not_analyzed'},
                'project': {'type': 'string', 'index': 'not_analyzed'},
                'machine_name': {'type': 'string', 'index': 'not_analyzed'},
                'timestamp': {'type': 'date'},
                'username': {'type': 'string', 'index': 'not_analyzed'},
            }
        }
    }
}


def _build_usage_dict(name, args):
    """Build dict of usage data.

    Args:
        name (str): function name
        args (tuple): args data

    Returns:
        (dict): usage dict
    """
    _usage = {
        'function': name,
        'machine_name': platform.node(),
        'project': os.environ.get('PSYOP_PROJECT'),
        'timestamp': datetime.datetime.utcnow(),
        'username': getpass.getuser(),
    }

    if args:
        _usage['args'] = str(args)

    # Add filename
    if host.NAME == 'maya':
        from maya import cmds
        _usage['filename'] = cmds.file(query=True, location=True)

    # Add cwd
    try:
        _usage['cwd'] = os.getcwd()
    except OSError:
        pass

    return _usage


def _write_usage_to_kibana(name=None, catch=True, args=None, verbose=0):
    """Write usage data to kibana index.

    Args:
        name (str): override function name
        catch (bool): on fail continue and disable usage tracking
        args (tuple): args data to write to usage
        verbose (int): print process data
    """

    # Don't track farm/dev usage
    if os.environ.get('USER') == 'render' or dev_mode():
        return

    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        return

    _start = time.time()
    _index_name = 'psyhive-'+datetime.datetime.utcnow().strftime('%Y.%m')
    _usage = _build_usage_dict(name=name, args=args)

    if verbose > 1:
        print _index_name
        pprint.pprint(_usage)

    # Send to kibana
    _conn = Elasticsearch([_ELASTIC_URL])
    if not _conn.ping():
        if catch:
            dprint('Failed to make connection to Elasticsearch')
            os.environ['PSYHIVE_DISABLE_USAGE'] = '1'
            return
        raise RuntimeError('Cannot connect to Elasticsearch database.')
    if not _conn.indices.exists(_index_name):
        _conn.indices.create(index=_index_name, body=_INDEX_MAPPING)
    _res = _conn.index(
        index=_index_name, doc_type=_ES_DATA_TYPE, body=_usage,
        id=_usage.pop('_id', None))
    _usage['_id'] = _res['_id']
    _dur = time.time() - _start
    dprint('Wrote usage to kibana ({:.02f}s)'.format(_dur), verbose=verbose)


def _write_usage_to_file(name, args, kwargs, verbose=1):
    """Append usage to daily text file for current user.

    The files are written in this both this and hvanderbeen test projects.

    Args:
        name (str): function name
        args (list): function args
        kwargs (dict): function kwargs
        verbose (int): print process data
    """
    _cur_proj = pipe.cur_project()

    # Compile data
    _data = {
        'cwd': abs_path(os.getcwd()),
        'time': int(time.time()),
        'name': name,
        'platform': sys.platform,
        'machine': platform.node(),
    }
    _kwargs_data = {}
    for _key, _val in kwargs.items():
        _kwargs_data[_key] = _clean_arg(_val)
    for _name, _val in [
            ('host', host.NAME),
            ('scene', host.cur_scene()),
            ('args', [_clean_arg(_arg) for _arg in args]),
            ('kwargs', _kwargs_data),
            ('proj', _cur_proj.name if _cur_proj else None),
    ]:
        if _val:
            _data[_name] = _val

    # Get list of projs to write to
    _projs = set()
    if _cur_proj:
        _projs.add(_cur_proj)
    _hv_proj = pipe.find_project('hvanderbeek_0001P', catch=True)
    if _hv_proj:
        _projs.add(_hv_proj)

    # Write data
    for _proj in _projs:
        _yml = File('{}/production/psyhive/usage/{}/{}.yml'.format(
            _proj.path, time.strftime('%y%m%d'), os.environ['USER']))
        lprint('\nWRITE USAGE!', name, args, kwargs, verbose=verbose)
        lprint(' -', _yml.path, verbose=verbose)
        _yml.write_yaml([_data], mode='a')


def _clean_arg(arg):
    """Clean the given arg for writing to yaml.

    For basic types, just use the value - otherwise convert to string.

    Args:
        arg (any): arg to clean

    Returns:
        (any): cleaned arg
    """
    if isinstance(arg, unicode):
        return str(arg)
    if isinstance(arg, (int, float, bool, six.string_types)):
        return arg
    return str(arg)


def get_usage_tracker(name=None, args=False, kibana=False, verbose=0):
    """Build usage tracker decorator.

    Args:
        name (str): override function name
        args (bool): store args/kwargs data
        kibana (bool): write to kibana
        verbose (int): print process data

    Returns:
        (fn): usage tracker decorator
    """

    def _track_usage(func):

        @functools.wraps(func)
        def _usage_tracked_fn(*args_, **kwargs):
            if (
                    not os.environ.get('USER') == 'render' and
                    not os.environ.get('PSYHIVE_DISABLE_USAGE')):
                if kibana:
                    _write_usage_to_kibana(
                        name=name or func.__name__, verbose=verbose,
                        args=(args_, kwargs) if args else None)
                _write_usage_to_file(
                    name=name or func.__name__, verbose=verbose,
                    args=args_, kwargs=kwargs)
            return func(*args_, **kwargs)

        return _usage_tracked_fn

    return _track_usage


def track_usage(func):
    """Decorator which writes to kibana each time a function is executed.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """
    return get_usage_tracker()(func)
