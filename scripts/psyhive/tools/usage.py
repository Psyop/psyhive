"""Tools for tracking tool usage using kibana."""

import datetime
import functools
import os
import pprint
import platform
import tempfile
import time

from psyhive import host
from psyhive.utils import dprint

ELASTIC_URL = 'http://la1dock001.psyop.tv:9200'
DATA_FILE = os.path.join(tempfile.gettempdir(), 'psyhive.json')
PROCESS_NAMES = None
GLOBAL_LOCK = None
OPEN_PROCS = dict()

ES_DATA_TYPE = 'data'
INDEX_MAPPING = {
    'mappings': {
        ES_DATA_TYPE: {
            'properties': {
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


def _write_usage_to_kibana(func, verbose=1):
    """Write usage data to kibana index.

    Args:
        func (fn): function that was executed
        verbose (int): print process data
    """

    # Don't track farm usage
    if os.environ.get('USER') == 'render':
        return

    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        return

    # Build usage dict
    _start = time.time()
    _index_name = 'psyhive-'+datetime.datetime.utcnow().strftime('%Y.%m.%d')
    _data = {
        'function': func.__name__,
        'machine_name': platform.node(),
        'project': os.environ.get('PSYOP_PROJECT'),
        'timestamp': datetime.datetime.utcnow(),
        'username': os.environ.get('USER'),
    }
    if host.NAME == 'maya':
        from maya import cmds
        _data['filename'] = cmds.file(query=True, location=True)
    if verbose > 1:
        print _index_name
        pprint.pprint(_data)

    # Send to kibana
    _conn = Elasticsearch([ELASTIC_URL])
    if not _conn.ping():
        raise RuntimeError('Cannot connect to Elasticsearch database.')
    if not _conn.indices.exists(_index_name):
        _conn.indices.create(index=_index_name, body=INDEX_MAPPING)
    _res = _conn.index(
        index=_index_name, doc_type=ES_DATA_TYPE, body=_data,
        id=_data.pop('_id', None))
    _data['_id'] = _res['_id']
    _dur = time.time() - _start
    dprint('Wrote usage to kibana ({:.02f}s)'.format(_dur), verbose=verbose)


def track_usage(func):
    """Decorator which writes to kibana each time a function is executed.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _usage_tracked_fn(*args, **kwargs):
        _write_usage_to_kibana(func)
        return func(*args, **kwargs)

    return _usage_tracked_fn
