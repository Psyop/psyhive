"""Tools for providing an actions browser in frasier."""

import os

from psyhive import qt, host, tk2, icons
from psyhive.tools import hive_bro
from psyhive.utils import get_single, abs_path, dprint

from . import _fr_work

DIALOG = None
_DIR = abs_path(os.path.dirname(__file__))
_UI_FILE = _DIR+'/_fr_action_browser.ui'


class _ActionBrowser(qt.HUiDialog3):
    """Browser for frasier actions."""

    def __init__(self, path=None):
        """Constructor.

        Args:
            path (str): jump to path
        """
        self._trg_path = path
        self._read_works()
        super(_ActionBrowser, self).__init__(ui_file=_UI_FILE)

    def init_ui(self):
        """Init ui elements."""
        self.ui.splitter.setSizes([314, 453])
        self._redraw__Character()

        _path = self._trg_path or host.cur_scene()
        if _path:
            self.jump_to(_path)

    def jump_to(self, path):
        """Jump browser to the given path.

        Args:
            path (str): path to jump to
        """
        print 'JUMPING TO', path

        try:
            _work = _fr_work.FrasierWork(path)
        except ValueError:
            return

        self.ui.Type.select_text([_work.type_])
        self.ui.Character.select_data([_work.get_root()])
        self.ui.Name.select_text([_work.name])
        self.ui.Desc.select_text([_work.desc])
        self.ui.Iteration.select_text(['{:02d}'.format(_work.iter)])
        self.ui.Work.select_data([_work])

        _sel_work = self.ui.WorkPath.text()
        if not path == _sel_work:
            print 'JUMP FAILED'
            print ' - PATH', path
            print ' - SEL ', _sel_work

    def _read_works(self, force=False):
        """Read work objects to display in the interface.

        Args:
            force (bool): force reread from disk
        """
        self.o_works = _fr_work.find_action_works(force=force)
        self.c_works = {}
        for _o_work in self.o_works:
            _c_work = tk2.obtain_cacheable(tk2.TTWork(_o_work.path))
            self.c_works[_o_work] = _c_work

    def _redraw__Character(self):
        _type = get_single(self.ui.Type.selected_text(), catch=True)

        _works = [_work for _work in self.o_works if _work.type_ == _type]
        _assets = sorted(set([_work.get_root() for _work in _works]))

        # Populate list
        self.ui.Character.blockSignals(True)
        self.ui.Character.clear()
        _items = []
        for _idx, _asset in enumerate(sorted(_assets)):
            _item = qt.HListWidgetItem(text=_asset.asset, data=_asset)
            _items.append(_item)
            self.ui.Character.addItem(_item)
        if _items:
            _items[0].setSelected(True)
        self.ui.Character.blockSignals(False)

        self._redraw__Name()

    def _redraw__Name(self, verbose=0):

        dprint('REDRAW NAME', verbose=verbose)

        # Get names
        _type = get_single(self.ui.Type.selected_text(), catch=True)
        _char = get_single(self.ui.Character.selected_data(), catch=True)
        _names = sorted(set([
            _work.name for _work in self.o_works
            if _work.type_ == _type and
            _work.get_root() == _char]))

        # Populate list
        self.ui.Name.blockSignals(True)
        self.ui.Name.clear()
        for _item in _names:
            self.ui.Name.addItem(_item)
        if _names:
            self.ui.Name.select_text(_names[0])
        self.ui.Name.blockSignals(False)

        self.ui.NameLabel.setText(_type)

        self._redraw__Desc()

    def _redraw__Desc(self, verbose=1):

        dprint('REDRAW DESC', verbose=verbose)

        _type = get_single(self.ui.Type.selected_text(), catch=True)
        _char = get_single(self.ui.Character.selected_text(), catch=True)
        _name = get_single(self.ui.Name.selected_text(), catch=True)
        _descs = sorted(set([
            _work.desc for _work in self.o_works
            if _work.type_ == _type and
            _work.asset == _char and
            _work.name == _name]))

        # Populate list
        self.ui.Desc.blockSignals(True)
        self.ui.Desc.clear()
        for _desc in _descs:
            self.ui.Desc.addItem(_desc)
        if _descs:
            self.ui.Desc.setCurrentRow(0)
        self.ui.Desc.blockSignals(False)

        self.ui.DescLabel.setText({'Name': 'Desc'}.get(_type, 'Desc'))

        self._redraw__Iteration()

    def _redraw__Iteration(self):

        # Get iterations
        _type = get_single(self.ui.Type.selected_text(), catch=True)
        _char = get_single(self.ui.Character.selected_data(), catch=True)
        _name = get_single(self.ui.Name.selected_text(), catch=True)
        _desc = get_single(self.ui.Desc.selected_text(), catch=True)
        _iters = sorted(set([
            _work.iter for _work in self.o_works
            if _work.type_ == _type and
            _work.get_root() == _char and
            _work.name == _name and
            _work.desc == _desc]))

        # Populate list
        self.ui.Iteration.blockSignals(True)
        self.ui.Iteration.clear()
        for _iter in _iters:
            _item = qt.HListWidgetItem('{:02d}'.format(_iter), data=_iter)
            self.ui.Iteration.addItem(_item)
        if _iters:
            self.ui.Iteration.setCurrentRow(0)
        self.ui.Iteration.blockSignals(False)

        self._redraw__Work()

    def _redraw__Work(self, verbose=0):

        dprint('POPULATE WORK', verbose=verbose)

        _type = get_single(self.ui.Type.selected_text(), catch=True)
        _char = get_single(self.ui.Character.selected_data(), catch=True)
        _name = get_single(self.ui.Name.selected_text(), catch=True)
        _desc = get_single(self.ui.Desc.selected_text(), catch=True)
        _iter = get_single(self.ui.Iteration.selected_data(), catch=True)
        _works = [
            _work for _work in self.o_works
            if _work.type_ == _type and
            _work.get_root() == _char and
            _work.iter == _iter and
            _work.name == _name and
            _work.desc == _desc]

        # Populate list
        self.ui.Work.setSpacing(2)
        self.ui.Work.blockSignals(True)
        self.ui.Work.clear()
        for _o_work in reversed(_works):
            _c_work = self.c_works[_o_work]
            _item = hive_bro.create_work_item(_c_work)
            _item.set_data(_o_work)
            self.ui.Work.addItem(_item)
        if _works:
            self.ui.Work.setCurrentRow(0)
        self.ui.Work.blockSignals(False)

        self._callback__Work()

    def _callback__Work(self):
        """Update work elements."""

        _work = get_single(self.ui.Work.selected_data(), catch=True)
        _c_work = self.c_works.get(_work)
        _cur_scene = host.cur_scene()
        _cur_work = tk2.cur_work()

        if _work:
            _cur_work_selected = (
                _cur_work.ver_fmt == _work.ver_fmt if _cur_work else False)
            _work_orig = _work.map_to(version=1)

            self.ui.WorkPath.setText(_work.path)
            self.ui.VendorMa.setText(_work_orig.get_vendor_file())
            _start, _end = [int(round(_val))
                            for _val in _work_orig.get_range()]
            self.ui.WorkLabel.setText(
                'Range: {:d} - {:d}'.format(_start, _end))

            self.ui.Load.setEnabled(True)
            self.ui.VersionUp.setEnabled(_cur_work_selected)
            self.ui.ExportFbx.setEnabled(_cur_work_selected)
            self.ui.WorkBrowser.setEnabled(True)
            self.ui.PlaySeq.setEnabled(bool(_c_work.find_outputs()))

        else:
            self.ui.WorkPath.setText('')
            self.ui.VendorMa.setText('')

            self.ui.Load.setEnabled(False)
            self.ui.VersionUp.setEnabled(False)
            self.ui.ExportFbx.setEnabled(False)
            self.ui.WorkBrowser.setEnabled(False)
            self.ui.PlaySeq.setEnabled(False)

    def _callback__Type(self):
        self._redraw__Character()

    def _callback__Character(self):
        self._redraw__Name()

    def _callback__Name(self):
        self._redraw__Desc()

    def _callback__Desc(self):
        self._redraw__Iteration()

    def _callback__Iteration(self):
        self._redraw__Work()

    def _callback__Load(self):
        _work = get_single(self.ui.Work.selected_data(), catch=True)
        if not _work:
            return
        _work.load()
        self._callback__Work()

    def _callback__VersionUp(self):
        self.ui.VersionUp.setEnabled(False)
        _cur_work = tk2.obtain_cur_work()
        _next_work = _cur_work.find_next()
        _comment = qt.read_input(
            'Enter comment:', title='Save new version', parent=self)
        _next_work.save(comment=_comment)

        self._read_works(force=True)
        self._redraw__Work()
        self.ui.VersionUp.setEnabled(True)

    def _callback__ExportFbx(self):
        _work = get_single(self.ui.Work.selected_data(), catch=True)
        _work_orig = _work.map_to(version=1)
        _work_orig.export_fbx(anim=True)

    def _callback__Magnet(self):
        _cur_scene = host.cur_scene()
        self.jump_to(_cur_scene)

    def _callback__WorkBrowser(self):

        _work = get_single(self.ui.Work.selected_data(), catch=True)
        _work.parent().launch_browser()

    def _callback__Refresh(self):
        self.ui.Refresh.setEnabled(False)
        host.refresh()
        _work_path = self.ui.WorkPath.text()
        self._read_works(force=True)
        if _work_path:
            self.jump_to(_work_path)
        self.ui.Refresh.setEnabled(True)

    def _callback__PlaySeq(self):

        _work = get_single(self.ui.Work.selected_data(), catch=True)
        if not _work:
            return
        _c_work = self.c_works[_work]
        _viewables = [_out for _out in _c_work.find_outputs()
                      if _out.format in ['mov', 'jpg']]

        if len(_viewables) == 1:
            _viewable = get_single(_viewables)
            _seq = get_single(_viewable.find_files())
            _seq.view()
            return

        _menu = qt.HMenu(self.ui.PlaySeq)
        for _viewable in _viewables:
            _seq = get_single(_viewable.find_files())
            _menu.add_action('View '+_viewable.output_type, func=_seq.view,
                             icon=icons.EMOJI.find('Blue Circle'))
        _pos = qt.get_p(self.ui.PlaySeq.size()/2)
        _menu.exec_(self.ui.PlaySeq.mapToGlobal(_pos))

    def _context__Work(self, menu):
        _work = get_single(self.ui.Work.selected_data(), catch=True)
        if not _work:
            return
        _c_work = self.c_works[_work]
        hive_bro.get_work_ctx_opts(
            menu=menu, parent=self, redraw_work=self._redraw__Work,
            work=_c_work)


def launch(path=None):
    """Launch action browser interface.

    Args:
        path (str): jump to path

    Returns:
        (_ActionBrowser): action browser instance
    """
    global DIALOG
    DIALOG = _ActionBrowser(path=path)
    return DIALOG
