"""Tools for managing ShaderBro interface."""

import os

from maya import cmds

from psyhive import icons, tk2, qt
from psyhive.tools import catch_error, get_usage_tracker
from psyhive.utils import (
    read_yaml, abs_path, store_result, get_single, dprint)

from maya_psyhive import ref
from maya_psyhive.utils import get_shps

ICON = icons.EMOJI.find("Palette")
_DIR = abs_path(os.path.dirname(__file__))
_UI_FILE = _DIR + '/shader_bro.ui'
DIALOG = None


class _ShaderBro(qt.HUiDialog3):
    """Shader browser for applying shader outputs."""

    shaders_data = None

    def __init__(self):
        """Constructor."""
        super(_ShaderBro, self).__init__(ui_file=_UI_FILE)
        self.set_icon(ICON)

    def init_ui(self):
        """Initiate ui elements."""
        self._read_shaders()
        self._redraw__Asset()

    def _read_shaders(self, parent=None):
        """Read published shader data.

        Args:
            parent (QWidget): parent widget (for progress bar)
        """
        self.shaders_data = _find_shaders(
            force=True, parent=self if parent else None)

    def _redraw__Asset(self):
        _assets = sorted(set([
            _shaders.asset for _shaders in self.shaders_data]))
        _items = [qt.HListWidgetItem(_asset) for _asset in _assets]
        self.ui.Asset.set_items(_items)

    def _redraw__Task(self):
        _asset = get_single(self.ui.Asset.selected_text(), catch=True)
        _tasks = sorted(set([
            _shaders.task for _shaders in self.shaders_data
            if _shaders.asset == _asset]))
        _items = [qt.HListWidgetItem(_task) for _task in _tasks]
        self.ui.Task.set_items(_items, select='shade')

    def _redraw__Version(self):
        _asset = self.ui.Asset.selected_text(single=True)
        _task = self.ui.Task.selected_text(single=True)
        _shds_mbs = sorted([
            _shaders for _shaders in self.shaders_data
            if _shaders.asset == _asset and
            _shaders.task == _task])

        self.ui.Version.blockSignals(True)
        self.ui.Version.clear()
        for _shds_mb in reversed(_shds_mbs):
            self.ui.Version.add_item(
                'v{:03d}'.format(_shds_mb.version), data=_shds_mb)
        self.ui.Version.blockSignals(False)
        self.ui.Version.currentIndexChanged.emit(0)

    def _redraw__Shader(self):
        _shd_mb = self.ui.Version.selected_data()
        print 'SHD MB', _shd_mb
        _shds = self.shaders_data.get(_shd_mb, [])
        self.ui.Shader.set_items(_shds)

    def _redraw__ApplyToSelection(self):
        _shd = self.ui.Shader.selected_text(single=True)
        self.ui.ApplyToSelection.setEnabled(bool(_shd))

    def _redraw__ImportShader(self):
        _shd = self.ui.Shader.selected_text(single=True)
        self.ui.ImportShader.setEnabled(bool(_shd))

    def _redraw__Work(self):
        _shd_mb = self.ui.Version.selected_data()
        if _shd_mb:
            _work = _shd_mb.map_to(tk2.TTWork, dcc='maya')
            _text = _work.path
        else:
            _text = ''
        self.ui.Work.setText(_text)

    def _redraw__WorkLoad(self):
        _shd_mb = self.ui.Version.selected_data()
        self.ui.WorkLoad.setEnabled(bool(_shd_mb))

    def _callback__Asset(self):
        self._redraw__Task()

    def _callback__Task(self):
        self._redraw__Version()

    def _callback__Version(self):
        dprint('CALLBACK VERSION')
        self._redraw__Shader()

    def _callback__Shader(self):
        self._redraw__ImportShader()
        self._redraw__ApplyToSelection()
        self._redraw__Work()
        self._redraw__WorkLoad()

    def _callback__WorkLoad(self):
        _work = tk2.TTWork(self.ui.Work.text())
        _work.load()

    def _callback__WorkRefresh(self):
        self._read_shaders(parent=True)
        self._redraw__Asset()

    def _callback__ImportShader(self):
        _shd = self.ui.Shader.selected_text(single=True)
        _shd_mb = self.ui.Version.selected_data()
        _import_shader(shd_mb=_shd_mb, shd_name=_shd, select=True)

    def _callback__ApplyToSelection(self):
        _shd = self.ui.Shader.selected_text(single=True)
        _shd_mb = self.ui.Version.selected_data()
        _assign_shader_to_sel(shd_mb=_shd_mb, shd_name=_shd, parent=self)


def _import_shader(shd_mb, shd_name, select=False):
    """Import the given shader into the current scene.

    The shaders mb file is referenced into the scene, the shader is
    duplicated from the reference and then the reference is removed.

    Args:
        shd_mb (TTOutputFile): published shaders mb file
        shd_name (str): name of shader to import
        select (bool): select the shading engine node

    Returns:
        (str): duplicated shading engine node
    """

    # Create duplicate of shader
    _tmpl = ref.create_ref(file_=shd_mb.path, namespace='_SB_TMP', force=True)
    _tmpl_se = _tmpl.get_node(shd_name)
    _se = cmds.duplicate(_tmpl_se, upstreamNodes=True)[0]
    _tmpl.remove(force=True)

    if select:
        cmds.select(_se, noExpand=True)

    return _se


def _assign_shader_to_sel(shd_mb, shd_name, parent):
    """Assign the given shader to selected geometry and shape nodes.

    Args:
        shd_mb (TTOutputFile): published shaders mb file
        shd_name (str): name of shader to import
        parent (QWidget): parent widget
    """
    print 'APPLY SHADER', shd_name, shd_mb.path

    # Get shape nodes of selections
    _shps = set(cmds.ls(selection=True, shapes=True))
    for _sel in cmds.ls(selection=True, type='transform'):
        _shps |= set(get_shps(_sel))
    _shps = sorted(_shps)
    if not _shps:
        qt.notify_warning(
            'No selected geometry or shapes found', parent=parent)
        return

    # Get shader
    _se = _import_shader(shd_mb=shd_mb, shd_name=shd_name)

    # Assign to shapes
    for _shp in _shps:
        cmds.sets(_shp, edit=True, forceElement=_se)


@store_result
def _find_shaders(force=False, parent=None, verbose=0):
    """Search current prject for shader outputs.

    Args:
        force (bool): reread cache from disk
        parent (QWidget): parent widget (for progress bar)
        verbose (int): print process data

    Returns:
        (dict): shader output, shader list
    """
    if force:
        tk2.clear_caches()

    _works = []
    for _asset in qt.progress_bar(
            tk2.obtain_assets(), 'Reading {:d} asset{}',
            parent=parent):
        _shade = _asset.find_step_root('shade', catch=True)
        if not _shade or not _shade.exists():
            continue
        for _work in _shade.find_work():
            _works.append(_work)

    _shd_mbs = {}
    for _work in qt.progress_bar(
            _works, 'Checking {:d} work file{}', parent=parent):

        _shd_mb = _work.map_to(
            tk2.TTOutputFile, extension='mb', output_name='main',
            output_type='shadegeo', format='shaders')
        _yml = _work.map_to(
            tk2.TTOutputFile, extension='yml', output_name='main',
            output_type='shadegeo', format='shaders')
        if not _shd_mb.exists() or not _yml.exists():
            continue

        _shds = read_yaml(_yml.path)
        _shd_mbs[_shd_mb] = _shds

        if verbose:
            print _work
            print _shds
            print

    return _shd_mbs


@get_usage_tracker('launch_shader_bro')
@catch_error
def launch():
    """Launch ShaderBro interface.

    Returns:
        (ShaderBro): dialog instance
    """
    global DIALOG
    DIALOG = _ShaderBro()
    return DIALOG
