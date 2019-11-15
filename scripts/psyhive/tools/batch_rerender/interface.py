"""Tools for managing the Batch Rerender interface."""

import os
import pprint

from psyhive import tk, qt, icons, farm
from psyhive.utils import (
    abs_path, get_plural, chain_fns, wrap_fn, dprint, lprint, safe_zip)

from psyhive.tools import get_usage_tracker

ICON = icons.EMOJI.find('Basket')


class _BatchRerenderUi(qt.HUiDialog):
    """Batch rerender interface."""

    def __init__(self):
        """Constructor."""
        from psyhive.tools import batch_rerender
        batch_rerender.DIALOG = self

        self._all_steps = []
        self._all_renders = []
        self._work_files = {}
        self._renders = []
        self._passes = []

        _ui_file = abs_path(
            'batch_rerender.ui', root=os.path.dirname(__file__))
        super(_BatchRerenderUi, self).__init__(ui_file=_ui_file)
        self.setWindowTitle('Batch Rerender')
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

        self.ui.steps.select_text('lighting')
        self.ui.tasks.select_text('lighting')

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
        self._work_files = {}
        for _render in self._renders:
            _latest_render = _render.find_latest()
            _work = _latest_render.find_work_file()
            _latest_work = _work.find_latest()
            if _work:
                if _work not in self._work_files:
                    self._work_files[_latest_work] = []
                self._work_files[_latest_work].append(_latest_render)

        widget.setText('Selected: {:d} render{} ({:d} work file{})'.format(
            len(self._renders), get_plural(self._renders),
            len(self._work_files), get_plural(self._work_files)))

    def _context__submit(self, menu):
        menu.add_action("Print renders + work files", chain_fns(
            wrap_fn(pprint.pprint, self._renders),
            wrap_fn(pprint.pprint, self._work_files.keys()),
            wrap_fn(pprint.pprint, self._passes)))
        menu.add_action("Print frame ranges", wrap_fn(
            self._read_frame_ranges, sorted(self._work_files), verbose=1))

    def _callback__submit(self):
        _work_files = sorted(self._work_files)
        _ranges = self._read_frame_ranges(_work_files)
        _rerender_work_files(
            work_files=_work_files, ranges=_ranges, passes=self._passes)

    def _read_frame_ranges(self, work_files, verbose=0):
        """Read frame range for each work file.

        This reads the frame range from all the selected passes for that
        work files and then takes the overall range from that.

        Args:
            work_files (TTWorkFileBase list): list of work files
            verbose (int): print process data

        Returns:
            (tuple list): list of start/end frames
        """
        _ranges = []
        for _work_file in qt.ProgressBar(
                work_files, 'Reading {:d} frame ranges'):
            dprint('READING', _work_file)
            _start, _end = None, None
            for _render in self._work_files[_work_file]:
                for _seq in _render.find_outputs():
                    _sstart, _send = _seq.find_range()
                    _start = (_sstart if _start is None
                              else min(_start, _sstart))
                    _end = (_send if _end is None
                            else max(_end, _send))
                    lprint(
                        '   - {:d}-{:d} {}'.format(
                            _sstart, _send, _seq.path),
                        verbose=verbose)
            print ' - RANGE {:d}-{:d} {}'.format(
                _start, _end, _work_file.path)
            _ranges.append((_start, _end))
            lprint(verbose=verbose)
        return _ranges

    def close(self):
        """Close interface."""
        self.ui.close()


def _rerender_work_files(work_files, ranges, passes):
    """Rerender the given work files on qube.

    Args:
        work_files (TTWorkFileBase list): work file list
        ranges (tuple list): list of start/end frames
        passes (str list): list of passes to rerender
    """
    _job = farm.MayaPyJob('Submit {:d} render{}'.format(
        len(work_files), get_plural(work_files)))
    for _work_file, _range in safe_zip(work_files, ranges):
        _py = '\n'.join([
            'import os',
            'os.environ["USERNAME"] = "{user}"  # For fileops/submit',
            'from psyhive import tk',
            'from maya_psyhive.tools import m_batch_rerender',
            '_path = "{work.path}"',
            '_range = {range}',
            '_passes = {passes}',
            '_work = tk.get_work(_path)',
            'm_batch_rerender.rerender_work_file(',
            '    range_=_range, work_file=_work, passes=_passes)',
        ]).format(work=_work_file, passes=passes, range=_range,
                  user=os.environ['USERNAME'])
        _task = farm.MayaPyTask(
            _py, label='Rerender {}'.format(_work_file.basename))
        _job.tasks.append(_task)

    _job.submit()


@get_usage_tracker(name='launch_batch_rerender')
def launch():
    """Launch batch rerender interface.

    Returns:
        (__BatchRerenderUi): interface instance
    """
    _dialog = _BatchRerenderUi()
    return _dialog
