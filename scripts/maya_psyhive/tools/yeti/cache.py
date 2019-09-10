"""Tools for managing yeti caching."""

import os

from maya import cmds

from psyhive import tk, host, qt, icons
from psyhive.utils import abs_path, get_single

from maya_psyhive import ref

ICON = icons.EMOJI.find('Ghost')


def _write_cache_from_selected_asset():
    """Cache selected rig."""
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning("No asset selected.\n\nPlease select the asset "
                          "you want to cache.")
        return
    _work = tk.cur_work()
    print 'REF', _ref

    # Get yeti nodes
    _yetis = _ref.find_nodes(type_='pgYetiMaya')
    if not _yetis:
        qt.notify_warning(
            "No yeti nodes in asset {}.\n\nThis asset cannot "
            "be cached.".format(_ref.namespace))
        return

    # Test outputs
    _kwargs = dict(format='fur', output_type='yeti',
                   extension='fur', output_name=_ref.namespace)
    for _yeti in _yetis:
        _out = _work.map_to(
            tk.TTShotOutputFileSeq, channel=str(_yeti).replace(':', '_'),
            **_kwargs)
        print 'OUT', _out
        if _out.exists():
            _out.delete(wording='Replace')
        _out.test_dir()

    # Generate caches
    cmds.select(_yetis)
    _out_path = _work.map_to(
        tk.TTShotOutputFileSeq, channel='<NAME>', **_kwargs).path
    print "OUT PATH", _out_path
    cmds.pgYetiCommand(
        writeCache=_out_path, range=host.t_range(), samples=3)


def _apply_cache_to_selected_asset(cache):
    """Apply cache to selected rig.

    Args:
        cache (str): path to cache file to apply
    """

    # Get asset
    _ref = ref.get_selected(catch=True)
    if not _ref:
        qt.notify_warning(
            "No asset selected.\n\nPlease select the asset you apply the "
            "cache to.")
        return
    print 'REF', _ref
    _yeti = get_single(_ref.find_nodes(type_='pgYetiMaya'))
    print 'YETI', _yeti

    _yeti.plug('cacheFileName').set_val(cache)
    _yeti.plug('fileMode').set_val(1)


class _YetiCacheToolsUi(qt.HUiDialog):
    """Interface for managing yeti caching."""

    def __init__(self):
        """Constructor."""
        self.work = tk.cur_work()
        self.shot = self.work.shot
        self.names = []

        _ui_file = abs_path(
            '{}/yeti_cache_tools.ui'.format(os.path.dirname(__file__)))
        super(_YetiCacheToolsUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self.ui.step.currentTextChanged.connect(self.ui.asset.redraw)
        self.ui.asset.currentTextChanged.connect(self.ui.version.redraw)
        self.ui.version.currentIndexChanged.connect(self.ui.cache_read.redraw)

    # @qt.list_redrawer
    def _redraw__step(self, widget):

        _steps = self.shot.find_step_roots()
        print 'WIDGET', widget

        # Update widget
        for _step in _steps:
            widget.add_item(_step.name, data=_step)
        if not _steps:
            widget.addItem('<None>')
        widget.setEnabled(bool(_steps))

    def _redraw__asset(self, widget):

        _step = self.ui.step.selected_data()

        self.names = []
        if not _step:
            _assets = []
        else:
            self.names = [_name for _name in _step.find_output_names()
                          if _name.output_type == 'yeti']
            _assets = sorted(set([_name.output_name for _name in self.names]))

        # Update widget
        widget.clear()
        widget.addItems(_assets)
        if not _assets:
            widget.addItem('<None>')
        widget.setEnabled(bool(_assets))

        self.ui.version.redraw()

    def _redraw__version(self, widget):

        _asset = self.ui.asset.currentText()
        print 'ASSET', _asset
        _name = get_single(
            [_name for _name in self.names if _name.output_name == _asset],
            catch=True)
        if not _name:
            _vers = []
        else:
            _vers = _name.find(depth=1, class_=tk.TTShotOutputVersion)

        # Update widget
        widget.clear()
        for _ver in _vers:
            widget.add_item(_ver.name, data=_ver)
        if _vers:
            widget.setCurrentIndex(len(_vers)-1)
        else:
            widget.addItem('<None>')
        widget.setEnabled(bool(_vers))

        self.ui.cache_read.redraw()

    def _redraw__cache_read(self, widget):
        _ver = self.ui.version.selected_data()
        widget.setEnabled(bool(_ver))

    def _callback__cache_write(self):
        _write_cache_from_selected_asset()

    def _callback__cache_read(self):

        _ver = self.ui.version.selected_data()
        _out = get_single(_ver.find_outputs())
        print 'OUTPUT', _out

        _apply_cache_to_selected_asset(cache=_out.path)


def launch_cache_tools():
    """Launch yeti cache tools interface."""
    _work = tk.cur_work()
    if not _work:
        qt.notify_warning(
            'No current work file found.\n\nPlease save your scene.')
    from maya_psyhive.tools import yeti
    yeti.DIALOG = _YetiCacheToolsUi()
    return yeti.DIALOG
