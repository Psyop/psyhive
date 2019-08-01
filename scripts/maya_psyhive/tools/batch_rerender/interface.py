"""Tools for managing the Batch Rerender interface."""

import os
import pprint

from psyhive import tk, qt, icons
from psyhive.utils import abs_path, get_plural, chain_fns, wrap_fn

from maya_psyhive.tools.batch_rerender import rerender

ICON = icons.EMOJI.find('Basket')
_DIALOG = None


class _BatchRerenderUi(qt.HUiDialog):
    """Batch rerender interface."""

    def __init__(self):
        """Constructor."""
        self._all_steps = []
        self._all_renders = []
        self._work_files = []
        self._renders = []
        self._passes = []

        _ui_file = abs_path(
            'batch_rerender.ui', root=os.path.dirname(__file__))
        super(_BatchRerenderUi, self).__init__(ui_file=_ui_file)
        self.set_icon(ICON)

        self.ui.sequences.itemSelectionChanged.connect(
            self.ui.shots.redraw)
        self.ui.shots.itemSelectionChanged.connect(
            self.ui.steps.redraw)
        self.ui.steps.itemSelectionChanged.connect(
            self.ui.tasks.redraw)
        self.ui.tasks.itemSelectionChanged.connect(
            self.ui.renders.redraw)
        self.ui.renders.itemSelectionChanged.connect(
            self.ui.info.redraw)

    @qt.list_redrawer
    def _redraw__sequences(self, widget):
        for _seq in tk.find_sequences():
            _item = qt.HListWidgetItem(_seq.name)
            _item.set_data(_seq)
            widget.addItem(_item)

    @qt.list_redrawer
    def _redraw__shots(self, widget):
        for _seq in self.ui.sequences.selected_data():
            for _shot in _seq.find_shots():
                _shot = tk.obtain_cacheable(_shot)
                _item = qt.HListWidgetItem(_shot.name)
                _item.set_data(_shot)
                widget.addItem(_item)

    @qt.list_redrawer
    def _redraw__steps(self, widget):
        _steps = set()
        self._all_steps = []
        for _shot in self.ui.shots.selected_data():
            for _step in _shot.find_step_roots():
                if not _step.find_renders():
                    continue
                self._all_steps.append(_step)
                _steps.add(_step.name)
        widget.addItems(sorted(_steps))

    @qt.list_redrawer
    def _redraw__tasks(self, widget):
        _step_names = self.ui.steps.selected_text()
        _tasks = set()
        self._all_renders = []
        for _step in self._all_steps:
            if _step.name not in _step_names:
                continue
            for _render in _step.find_renders():
                _tasks.add(_render.task)
                self._all_renders.append(_render)
        widget.addItems(sorted(_tasks))

    @qt.list_redrawer
    def _redraw__renders(self, widget):
        _tasks = self.ui.tasks.selected_text()
        _renders = [_render for _render in self._all_renders
                    if _render.task in _tasks and
                    _render.find_latest().find_work_file()]
        _render_names = sorted(set([
            _render.output_name for _render in _renders]))
        widget.addItems(sorted(_render_names))

    def _redraw__info(self, widget):

        _passes = self.ui.renders.selected_text()
        _tasks = self.ui.tasks.selected_text()

        self._renders = [_render for _render in self._all_renders
                         if _render.output_name in _passes and
                         _render.task in _tasks]
        self._passes = sorted(set([
            _render.output_name for _render in self._renders]))

        # Find latest work files
        self._work_files = set()
        for _render in self._renders:
            _work = _render.find_latest().find_work_file()
            if _work:
                self._work_files.add(_work.find_latest())
        self._work_files = sorted(self._work_files)

        widget.setText('Selected: {:d} render{} ({:d} work file{})'.format(
            len(self._renders), get_plural(self._renders),
            len(self._work_files), get_plural(self._work_files)))

    def _context__submit(self, menu):
        menu.add_action("Print renders + work files", chain_fns(
            wrap_fn(pprint.pprint, self._renders),
            wrap_fn(pprint.pprint, self._work_files),
            wrap_fn(pprint.pprint, self._passes)))

    def _callback__submit(self):

        rerender.rerender_work_files(
            work_files=self._work_files, passes=self._passes)


def launch():
    """Launch batch rerender interface.

    Returns:
        (_BatchRerenderUi): interface instance
    """
    global _DIALOG
    _DIALOG = _BatchRerenderUi()

    _DIALOG.ui.steps.select_text('lighting')
    _DIALOG.ui.tasks.select_text('lighting')
    print _DIALOG.ui.tasks

    return _DIALOG
