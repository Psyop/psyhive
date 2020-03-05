"""Psylaunch addon config file for psyhive."""

import os

from psylaunch.addons import MayaModule


class PsyHive(MayaModule):
    """PsyHive psylaunch module."""

    def setup(self):
        """Executed on application launch."""

        _env_root = os.path.join(
            os.environ.get('PSYOP_PROJECT_BRANCH_PATH'),
            'addons', 'maya', 'psyhive')
        _py_root = os.path.join(_env_root, 'scripts')
        _plugin_path = os.path.join(_env_root, 'plugins')

        # self.env.set('ENV_ROOT', _env_root)
        # self.env.set('TOOLS_ROOT', tools_root)
        # self.env.set('PROJ_ROOT', env_root)
        # content_root_path = 'work/Frasier/frasier/Content'

        # if os.path.exists(os.path.join("D:", content_root_path)):
        #     export_root = os.path.join("D:", content_root_path)
        # elif os.path.exists("W:\\"):
        #     export_root = os.path.join("W:", content_root_path)
        # else:
        #     export_root = os.path.join("C:", content_root_path)
        # self.env.set('EXPORT_ROOT', content_root_path)

        self.env.append_to_env('PYTHONPATH', _py_root)

        # assert os.path.exists(_PLUGIN_DIR)
        if _plugin_path not in os.environ['MAYA_PLUG_IN_PATH'].split(';'):
            os.environ['MAYA_PLUG_IN_PATH'] += ';'+_plugin_path

        # ART_TOOLS_FRASIER_DEV = 'p4 sync //art_tools/frasier_dev/... #head'
        # FRASIER_ART_TOOLS = 'p4 sync //frasier/sourceart/Tools... #head'
        # self.env.set('HSL_PROJECT_WORKFLOW', FRASIER_ART_TOOLS)
        # self.env.set('HSL_PROJECT_NAME', "frasier")
        # self.env.set('PROJ_MAYA_SETUNITS', True)

    def on_startup(self):
        """Executed in application startup."""

        # import art_tools
        # art_tools.startup()

        # from maya import cmds
        # from maya_psyhive.shows import frasier
        # cmds.evalDeferred(frasier.install_hsl_tools)
