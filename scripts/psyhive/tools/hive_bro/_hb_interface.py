"""Tools for testing HiveBro."""

import operator
import os

from psyhive import qt, icons, host, tk2
from psyhive.utils import (
    get_single, wrap_fn, abs_path, apply_filter, lprint, safe_zip, val_map,
    copy_text)

from . import _hb_work, _hb_utils

DIALOG = None
ICON = icons.EMOJI.find('Honeybee')
_DIR = abs_path(os.path.dirname(__file__))
UI_FILE = _DIR+'/hive_bro.ui'


class _HiveBro(qt.HUiDialog3):
    """HiveBro interface."""

    def __init__(self, path=None):
        """Constructor.

        Args:
            path (str): jump interface to path
        """
        self._asset_roots = tk2.obtain_assets()
        self._work_files = []

        super(_HiveBro, self).__init__(ui_file=UI_FILE)

        _path = path or host.cur_scene()
        if _path:
            self.jump_to(_path)

    def init_ui(self):
        """Initiate ui elements before load settings."""
        self._redraw__AssetType()

    def _redraw__AssetType(self):

        _types = sorted(set([
            _root.sg_asset_type for _root in self._asset_roots]))

        self.ui.AssetType.blockSignals(True)
        self.ui.AssetType.clear()
        for _type in _types:
            self.ui.AssetType.addItem(_type)
        self.ui.AssetType.setCurrentRow(0)
        self.ui.AssetType.blockSignals(False)

        self._redraw__Asset()
        self._redraw__Sequence()

    def _redraw__Asset(self):

        _type = get_single(self.ui.AssetType.selected_text(), catch=True)
        _assets = [_asset for _asset in self._asset_roots
                   if _asset.sg_asset_type == _type]
        _filter = self.ui.AssetFilter.text()
        if _filter:
            _assets = apply_filter(
                _assets, _filter, key=operator.attrgetter('asset'))

        self.ui.Asset.blockSignals(True)
        self.ui.Asset.clear()
        for _asset in _assets:
            _item = qt.HListWidgetItem(_asset.asset, data=_asset)
            self.ui.Asset.addItem(_item)
        self.ui.Asset.setCurrentRow(0)
        self.ui.Asset.blockSignals(False)

        self._callback__Asset()

    def _redraw__Sequence(self):

        self.ui.Sequence.blockSignals(True)
        for _seq in tk2.obtain_sequences():
            _item = qt.HListWidgetItem(_seq.sequence, data=_seq)
            self.ui.Sequence.addItem(_item)
        self.ui.Sequence.setCurrentRow(0)
        self.ui.Sequence.blockSignals(False)

        self._callback__Sequence()

    def _redraw__Shot(self):

        _seq = get_single(self.ui.Sequence.selected_data(), catch=True)
        _filter = self.ui.ShotFilter.text()
        _shots = _seq.find_shots(filter_=_filter) if _seq else []

        self.ui.Shot.blockSignals(True)
        self.ui.Shot.clear()
        for _shot in _shots:
            _item = qt.HListWidgetItem(_shot.shot, data=_shot)
            self.ui.Shot.addItem(_item)
        self.ui.Shot.setCurrentRow(0)
        self.ui.Shot.blockSignals(False)

        self._callback__Shot()

    def _redraw__Step(self):

        # Get step root
        _mode = self.ui.RootTabs.cur_text()
        if _mode == 'Assets':
            _root = get_single(self.ui.Asset.selected_data(), catch=True)
        elif _mode == 'Shots':
            _root = get_single(self.ui.Shot.selected_data(), catch=True)
        else:
            raise ValueError(_mode)
        _steps = _root.find_step_roots() if _root else []

        # Populate list
        _cur = self.ui.Step.selected_text(single=True)
        self.ui.Step.blockSignals(True)
        self.ui.Step.clear()
        _sel = _cur if _cur in _steps else None
        for _step in _steps:
            _work_area = _step.get_work_area(dcc=_hb_utils.cur_dcc())
            _col = 'grey'
            if os.path.exists(_work_area.yaml):
                _col = 'white'
                _sel = _sel or _step
            _item = qt.HListWidgetItem(_step.step, data=_step)
            _item.set_col(_col)
            self.ui.Step.addItem(_item)
        if _sel:
            self.ui.Step.select_data([_sel])
        else:
            self.ui.Step.setCurrentRow(0)
        self.ui.Step.blockSignals(False)

        self._callback__Step()

    def _redraw__Task(self):

        _step = get_single(self.ui.Step.selected_data(), catch=True)

        self._work_files = []
        if _step:
            _work_area = _step.get_work_area(dcc=_hb_utils.cur_dcc())
            self._work_files = _work_area.find_work()

        # Find mtimes of latest work versions
        _tasks = sorted(set([
            _work.task for _work in self._work_files]))
        _latest_works = [
            [_work for _work in self._work_files if _work.task == _task][-1]
            for _task in _tasks]
        _mtimes = [
            _work.get_mtime() for _work in _latest_works]

        # Clear task edit
        self.ui.TaskEdit.blockSignals(True)
        self.ui.TaskEdit.setText('')
        self.ui.TaskEdit.blockSignals(False)

        # Add to widget
        self.ui.Task.blockSignals(True)
        self.ui.Task.clear()
        for _task, _mtime in safe_zip(_tasks, _mtimes):
            _item = qt.HListWidgetItem(_task)
            if len(set(_mtimes)) == 1:
                _col = qt.HColor('white')
            else:
                _fr = val_map(
                    _mtime, in_min=min(_mtimes), in_max=max(_mtimes))
                _col = qt.HColor('Grey').whiten(_fr)
            _item.set_col(_col)
            self.ui.Task.addItem(_item)
        if _step in _tasks:
            self.ui.Task.select_text([_step])
        else:
            self.ui.Task.setCurrentRow(0)
        self.ui.Task.blockSignals(False)

        self._redraw__Work()

    # def _redraw__TaskEdit(self):
    #     _task = get_single(self.ui.Task.selected_text(), catch=True)
    #     self.ui.TaskEdit.widget.setText(_task)

    def _redraw__Work(self):

        # Find work files
        _task = (
            self.ui.TaskEdit.text() or
            get_single(self.ui.Task.selected_text(), catch=True))
        _work_files = [
            _work for _work in self._work_files
            if _work.task == _task]
        if _work_files:
            _work_data = _work_files[0].get_work_area().get_metadata()

        # Add items
        self.ui.Work.blockSignals(True)
        self.ui.Work.clear()
        for _idx, _work_file in enumerate(reversed(_work_files)):
            _item = _hb_work.create_work_item(_work_file, data=_work_data)
            self.ui.Work.addItem(_item)
        self.ui.Work.setCurrentRow(0)
        self.ui.Work.blockSignals(False)

        self._callback__Work()

    def _redraw__WorkLoad(self):
        _ver = self.ui.Work.selected_data()
        self.ui.WorkLoad.setEnabled(bool(_ver))

    def _redraw__WorkPath(self):

        _work = get_single(self.ui.Work.selected_data(), catch=True)
        _task = self.ui.TaskEdit.text()
        _step = get_single(self.ui.Step.selected_data(), catch=True)

        if not _work and _task and _step:
            _dcc = _hb_utils.cur_dcc()
            _hint = '{dcc}_{area}_work'.format(dcc=_dcc, area=_step.area)
            _work = _step.map_to(
                hint=_hint, class_=tk2.TTWork, Task=_task,
                extension=tk2.get_extn(_dcc), version=1)
        self.ui.WorkPath.setText(_work.path if _work else '')

    def _redraw__WorkSave(self):

        _sel_work = get_single(self.ui.Work.selected_data(), catch=True)
        _task = self.ui.Task.selected_data()
        _cur_work = tk2.obtain_cur_work()
        if not _sel_work or not _cur_work:
            _enabled = False
        else:
            _enabled = _sel_work == _cur_work
        self.ui.WorkSave.setEnabled(_enabled)

    def _redraw__WorkSaveAs(self):

        _sel_work = get_single(self.ui.Work.selected_data(), catch=True)
        _work_path = self.ui.WorkPath.text()
        _task = self.ui.Task.selected_data()
        _cur_work = tk2.obtain_cur_work()

        _enabled = True
        _text = 'Save As'
        if not _work_path:
            _enabled = False
        elif (
                _sel_work and _cur_work and
                _sel_work.ver_fmt == _cur_work.ver_fmt):
            _text = 'Version Up'

        self.ui.WorkSaveAs.setEnabled(_enabled)
        self.ui.WorkSaveAs.setText(_text)

    def _redraw__WorkView(self, widget):
        _work = get_single(self.ui.Work.selected_data(), catch=True)
        widget.setEnabled(bool(_work and _work.find_seqs()))

    def _callback__RootTabs(self):
        self._redraw__Step()

    def _callback__AssetType(self):
        self._redraw__Asset()

    def _callback__AssetFilter(self):
        self._redraw__Asset()

    def _callback__AssetFilterClear(self):
        self.ui.AssetFilter.setText('')

    def _callback__Asset(self):
        self._redraw__Step()

    def _callback__Sequence(self):
        self._redraw__Shot()

    def _callback__Shot(self):
        self._redraw__Step()

    def _callback__ShotFilterClear(self):
        self.ui.ShotFilter.setText('')

    def _callback__Step(self):
        self._redraw__Task()

    def _callback__Task(self):
        _task = get_single(self.ui.Task.selected_text(), catch=True)
        self.ui.TaskEdit.setText(_task)
        self._redraw__Work()

    def _callback__TaskEdit(self):
        _text = self.ui.TaskEdit.text()
        self.ui.Task.blockSignals(True)
        if not _text:
            self.ui.Task.redraw()
        elif _text in self.ui.Task.all_text():
            self.ui.Task.select_text(_text)
        else:
            self.ui.Task.clearSelection()
        self.ui.Task.blockSignals(False)
        self._redraw__Work()

    def _callback__TaskRefresh(self):
        _sel_work = self.ui.Work.selected_data(single=True)
        tk2.clear_caches()
        self._redraw__Task()
        if _sel_work:
            self.jump_to(_sel_work.path)

    def _callback__Work(self):

        self._redraw__WorkPath()
        self._redraw__WorkLoad()
        self._redraw__WorkSave()
        self._redraw__WorkSaveAs()

    def _callback__WorkCopy(self):
        _work = get_single(self.ui.Work.selected_data())
        copy_text(_work.path)

    def _callback__WorkLoad(self):

        _ver = get_single(self.ui.Work.selected_data(), catch=True)
        self.ui.WorkLoad.setEnabled(False)
        host.refresh()
        _ver.load()
        self.ui.WorkLoad.setEnabled(True)
        self._callback__Work()

    def _callback__WorkJumpTo(self):
        _file = host.cur_scene()
        self.jump_to(_file)

    def _callback__WorkRefresh(self):
        _work = get_single(self.ui.Work.selected_data())
        tk2.clear_caches()
        _work.find_outputs()
        self.ui.Task.redraw()
        self.jump_to(_work.path)

    def _callback__WorkSaveAs(self):

        _work_path = self.ui.WorkPath.text()
        _cur_work = tk2.cur_work()
        _next_work = tk2.obtain_work(_work_path).find_next()

        # Apply change task warning
        if _cur_work:

            _cur_task = _cur_work.get_work_area(), _cur_work.task
            _next_task = _next_work.get_work_area(), _next_work.task

            print 'CUR WORK ', _cur_work
            print 'NEXT WORK', _next_work

            if _cur_task != _next_task:
                _icon = _hb_work.get_work_icon(_next_work)
                qt.ok_cancel(
                    'Are you sure you want to switch to a different task?'
                    '\n\nCurrent:\n{}\n\nNew:\n{}'.format(
                        _cur_work.path, _next_work.path),
                    title='Switch task', icon=_icon)

        # Save
        self.ui.WorkSaveAs.setEnabled(False)
        _comment = qt.read_input(
            'Enter comment:', title='Save new version', parent=self)
        _next_work.save(comment=_comment)

        # Update ui
        self._callback__TaskRefresh()
        self._callback__WorkJumpTo()

        self.ui.WorkSaveAs.setEnabled(True)

    def _callback__WorkSave(self):

        self.ui.WorkSave.setEnabled(False)
        _work = get_single(self.ui.Work.selected_data())
        _comment = qt.read_input(
            'Enter comment:', title='Save new version', parent=self)
        _work.save_inc(comment=_comment)
        self.ui.WorkSave.setEnabled(True)

    def _callback__WorkView(self):
        _work = get_single(self.ui.Work.selected_data())
        _seq = get_single(_work.find_seqs())
        _seq.view()

    def _context__Step(self, menu):
        _step = get_single(self.ui.Step.selected_data(), catch=True)
        if _step:
            menu.add_action(
                'Copy path', wrap_fn(copy_text, _step.path), icon=icons.COPY)

    def _context__Work(self, menu):
        _work = get_single(self.ui.Work.selected_data(), catch=True)
        if _work:
            _hb_work.get_work_ctx_opts(
                work=_work, menu=menu, redraw_work=self._redraw__Work,
                parent=self)

    def _context__WorkJumpTo(self, menu):

        _work = get_single(self.ui.Work.selected_data(), catch=True)

        # Add jump to recent options
        menu.add_label("Jump to")
        for _work in _hb_work.get_recent_work():
            _work = _work.find_latest()
            if not _work:
                continue
            _label = _hb_work.get_work_label(_work)
            _icon = _hb_work.get_work_icon(_work, mode='basic')
            _fn = wrap_fn(self.jump_to, _work.path)
            menu.add_action(_label, _fn, icon=_icon)

        menu.addSeparator()

        # Jump to clipboard work
        _clip_work = tk2.get_work(qt.get_application().clipboard().text())
        if _clip_work:
            _label = _hb_work.get_work_label(_clip_work)
            _fn = wrap_fn(self.jump_to, _clip_work.path)
            menu.add_action('Jump to '+_label, _fn, icon=icons.COPY)
        else:
            menu.add_label('No work in clipboard', icon=icons.COPY)

        # Add current work to recent
        if _work:
            menu.add_action(
                'Add selection to recent', _work.add_to_recent,
                icon=icons.EMOJI.find('Magnet'))

    def jump_to(self, path, verbose=1):
        """Point HiveBro to the given path.

        Args:
            path (str): path to apply
            verbose (int): print process data
        """
        lprint("SELECT PATH", path, verbose=verbose)
        _shot = tk2.get_shot(path)
        _step = tk2.get_step_root(path)
        _work = tk2.get_work(path)

        if not _shot:
            self.ui.RootTabs.setCurrentIndex(0)
        else:
            self.ui.RootTabs.setCurrentIndex(1)

        if _step:
            if not _shot:
                self.ui.AssetType.select_text([_step.sg_asset_type])
                self.ui.Asset.select_text([_step.asset])
            else:
                self.ui.Sequence.select_text([_step.sequence])
                self.ui.ShotFilter.setText('')
                self.ui.Shot.select_text([_step.shot])
            self.ui.Step.select_text([_step.step])

        if _work:
            self.ui.Task.select_text([_work.task])
            self.ui.Work.select_data([_work])


def launch(path=None):
    """Launch HiveBro interface.

    Args:
        path (str): apply path on launch

    Returns:
        (HiveBro): hive bro instance
    """
    from psyhive.tools import hive_bro
    global DIALOG

    tk2.clear_caches()
    print 'Launching HiveBro'
    DIALOG = _HiveBro(path=path)
    hive_bro.DIALOG = DIALOG

    return DIALOG
