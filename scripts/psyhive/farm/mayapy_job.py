"""Tools for managing mayapy jobs.

The local flag allows the job to be executed on the local machine.

To set this up:

    Start
        > services
        > qubeworker (right-click)
        > stop
    Explorer
        > C:/Program Files/pfx/qube/sbin (shift-right-click)
        > Open Powershell window here
        > Enter "worker --desktop"

"""

import os
import time

import psyrc
import psyop

from psyq.job import Job, JobGraph, WorkItem
from psyq.engines.qube import QubeSubmitter

import psyhive
from psyhive import pipe, tk
from psyhive.utils import abs_path, write_file, lprint, dev_mode


def _get_app_version():
    """Get current maya version.

    Returns:
        (str): maya version
    """
    try:
        from psyq.jobs.maya.maya_util import get_app_version
    except ImportError:
        pass
    else:
        return get_app_version()

    return pipe.cur_project().read_psylaunch_cfg()['apps']['maya']['default']


class MayaPyJob(object):
    """Represents a qube job."""

    def __init__(self, label, tasks=None, uid=None):
        """Constructor.

        Args:
            label (str): job label
            tasks (_MayaPyTask list): list of tasks
            uid (str): apply uid to this job
        """
        self.uid = uid
        self.label = label
        self.tasks = tasks or []
        self.procs = 1

    def submit(self, local=None, submit=True, modules=None, verbose=1):
        """Submit this job to qube.

        Args:
            local (bool): prepare job for local execute
            submit (bool): submit to qube
            modules (mod list): modules to add to sys.path in local mode
            verbose (int): print process data
        """
        _local = local or os.environ.get('PSYHIVE_FARM_LOCAL_SUBMIT')
        _uid = self.uid or _get_uid()
        _tmp_dir = _get_tmp_dir(uid=_uid)
        _tmp_fmt = '{}/task.{{}}.py'.format(_tmp_dir)
        _work = tk.cur_work()

        # Create job
        _label = '{}: {}'.format(pipe.cur_project().name, self.label)
        _job = Job(label=_label)
        _job.worker = "psyhive_mayapy"
        _job.fixture.environ = _get_job_environ(local=_local)
        _job.payload = {
            'app_version': _get_app_version(),
            'py_dir': _tmp_dir}

        # Setup job for local execute
        if _local:

            _job.extra['qube.reservations'] = (
                "global_host.qube=1,host.processors={procs:d}".format(
                    procs=self.procs))
            _job.extra['qube.hosts'] = os.getenv('COMPUTERNAME')
            _job.extra['qube.groups'] = ""
            _job.extra['qube.restrictions'] = ""
            _job.extra['qube.cluster'] = ""

            _mods = (modules or []) + [psyhive]
            for _mod in _mods:
                _dir = os.path.dirname(os.path.dirname(_mod.__file__))
                _path = abs_path(_dir).replace('/', u'\\')
                _job.fixture.environ['PYTHONPATH'] += ';{}'.format(_path)

        # Add tasks
        lprint('TMP FMT', _tmp_fmt, verbose=verbose)
        for _idx, _task in enumerate(self.tasks):

            # Write file to disk
            _n_str = '{:04d}'.format(_idx+1)
            _tmp_py = _tmp_fmt.format(_n_str)
            write_file(file_=_tmp_py, text=_task.get_py(tmp_py=_tmp_py))
            lprint(' -', _tmp_py, verbose=verbose)
            _payload = {'pyfile': _tmp_py}

            # Create work item
            _work_item = WorkItem(label=_task.label, payload=_payload)
            _job.work_items.append(_work_item)

        # Submit
        _job_graph = JobGraph()
        _job_graph.add_job(_job)
        _submitter = QubeSubmitter()
        if submit:
            _result = _submitter.submit(_job_graph)
            lprint('RESULT', _result, verbose=verbose > 1)


def _get_tmp_root():
    """Get tmp dir for qube submissions."""
    return abs_path(
        r'P:\global\distribution\lam\projects\{}/data/psyhive'.format(
            pipe.cur_project().name))


def _get_tmp_dir(uid):
    """Get tmp dir for the given uid.

    Args:
        uid (str): submission uid

    Returns:
        (str): path to job tmp dir
    """
    return '{}/qube/job_{}'.format(_get_tmp_root(), uid)


def _get_uid():
    """Generate a uid for qube submission.

    Returns:
        (str): uid
    """
    return time.strftime('%y%m%d_%H%M%S')


def _get_job_environ(local=False):
    """Get environment for psyq job.

    Args:
        local (bool): if job is being executed locally

    Returns:
        (dict): environ
    """
    _result = {}
    _result.update(psyop.env.get_bootstrap_variables())

    # Update python path
    _clean_env = psyrc.original_environment()
    _result["PYTHONPATH"] = _clean_env.get("PYTHONPATH", "")

    # Set psyq plugin path
    if dev_mode() and not local:
        _plugin_path = (
            'P:/projects/hvanderbeek_0001P/code/primary/addons/'
            'maya/modules/psyhive/scripts/psyhive/farm/psyq_plugin')
    else:
        _plugin_path = abs_path(os.path.dirname(__file__)+'/psyq_plugin')
    print "PSYQ_PLUGIN_PATH", _plugin_path
    _result["PSYQ_PLUGIN_PATH"] = _plugin_path

    return _result
