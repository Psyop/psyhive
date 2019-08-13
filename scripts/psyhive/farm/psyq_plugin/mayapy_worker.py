"""Plugin for psyq allow farm execution of arbitrary python code."""

import pprint
import sys
import os

from psyq.worker import BasicWorker
import psylaunch


def _force_exit(code):
    """Forcibly exit the current process, skipping python teardown.

    This is to catch mayapy crashing on exit (apparently due to sceneAssembly
    plugin). Attempts to flush output buffers and terminate the process
    immediately, before mayapy has a chance to crash and/or hang.

    Args:
        code (int): exit code
    """
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    finally:
        os._exit(code)


def _scene_assembly_plugin_loaded():
    """Returns whether the maya scene assembly plugin is currenty loaded.

    This is part of a workaround for stability issues that this plugin
    causes on exit from mayapy. If maya is not currently running, this
    should return False.
    """
    try:
        from maya import cmds
    except ImportError:
        return False
    if not hasattr(cmds, 'pluginInfo'):
        return False
    return cmds.pluginInfo("sceneAssembly", query=True, loaded=True)


class MayaPyWorker(BasicWorker):
    """Worker class for rendering Maya scenes."""

    def exec_subprocess(self, script_file):
        """Reimplemented from BasicWorker.

        Args:
            script_file (str): path to execution py

        Returns:
            (any): app launch result
        """

        # Get launcher arguments for psylaunch
        print '[worker] EXEC MAYA SUBPROCESS'
        _app_name = self.payload.get("app_name", "mayapy")
        _app_ver = self.payload.get("app_version")
        _args = [script_file]

        # Launch and wait for maya batch process.
        print '[worker] LAUNCHING MAYA', _app_name, _app_ver, _args
        _result = psylaunch.launch_app(
            _app_name, version=_app_ver, args=_args, wait=True)
        print '[worker] LAUNCHED APP', _result

        return _result

    def begin_work(self):
        """Reimplemented from BasicWorker."""
        print '[worker] BEGINNING WORK', pprint.pformat(self.payload)

        print '[worker] STARTING MAYA STANDALONE'
        from maya import standalone
        standalone.initialize()

    def process_work_item(self, item):
        """Reimplemented from BasicWorker.

        Args:
            item (WorkItem): item being executed
        """
        print "[worker] PROCESSING WORK ITEM", item.label
        _py = item.payload['pyfile']
        print '[worker] EXECUTING PYFILE', _py
        execfile(_py)
        print '[worker] COMPLETED WORK ITEM', item.label

    def end_work(self):
        """Executed on work completion."""
        if _scene_assembly_plugin_loaded():
            print '[worker] FORCING EXIT DUE TO SCENE ASSEMBLY PLUGIN'
            _force_exit(0)
        print '[worker] ENDED WORK'


def initialize_plugin(reg):
    """Initialize plugin.

    Args:
        reg (PluginFactory): psyq plugin factory instance
    """
    print "[worker] INITIALISING PLUGIN MayaPyWorker", reg, type(reg)
    reg.register_plugin("psyhive_mayapy", MayaPyWorker)
