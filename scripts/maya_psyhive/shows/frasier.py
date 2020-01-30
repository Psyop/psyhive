"""Tools for frasier_38732V project."""

import sys
import os

from psyhive import icons

ICON = icons.EMOJI.find('Brain')
_ROOT = ('P:/projects/frasier_38732V/code/primary/addons/general/'
         'frasier/_ToolsPsy')
_PY_ROOT = _ROOT+'/release/maya/v2018/hsl/python'


def install_hsl_tools():
    """Install Hardsuit-Labs tools."""
    os.environ['MAYA_START_MELSCRIPT'] = _ROOT+(
        '/release/maya/v2018/hsl/MEL/launch_scripts/'
        'maya_2018_startup_frasier.mel')

    _3rd_party_root = _ROOT+'/release/maya/v2018/3rdparty/python'
    for _root in [_PY_ROOT, _3rd_party_root]:
        while _root in sys.path:
            sys.path.remove(_root)
        sys.path.insert(0, _root)

    import art_tools
    art_tools.startup()


def launch_anim_exporter():
    """Launch hsl anim exporter."""
    install_hsl_tools()
    import art_tools
    reload(art_tools)
    from art_tools.gui.qt.dialog import animation_exporter_2
    animation_exporter_2.open_tool()
