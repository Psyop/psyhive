"""Tools for testing HiveBro."""

import os
import time

from psyhive import qt, icons, host, pipe, tk2
from psyhive.qt import QtCore, QtGui
from psyhive.utils import (
    get_single, wrap_fn, abs_path, store_result, system,
    get_time_t, get_owner, chain_fns, passes_filter, lprint,
    safe_zip, val_map, copy_text, str_to_seed,
    launch_browser, Seq, store_result_on_obj)

UI_FILE = abs_path('hive_bro.ui', root=os.path.dirname(__file__))


class _HiveBroAssets(object):
    """Assets tab of HiveBro."""

    ui = None
    _add_work_ctx_opts = None

    def __init__(self):
        """Constructor."""
        self._asset_roots = tk2.obtain_assets()
        self._asset_work_files = []

    def connect_signals(self):
        """Connect signals."""
        self.ui.asset_type.itemSelectionChanged.connect(
            self.ui.asset.redraw)
        self.ui.asset_filter.textChanged.connect(
            self.ui.asset.redraw)

    @qt.list_redrawer
    def _redraw__asset_type(self, widget):
        _types = sorted(set([
            _root.sg_asset_type for _root in self._asset_roots]))
        widget.addItems(_types)

    @qt.list_redrawer
    def _redraw__asset(self, widget):
        _type = get_single(self.ui.asset_type.selected_text(), catch=True)
        _filter = self.ui.asset_filter.text()

        for _asset in self._asset_roots:
            if not _asset.sg_asset_type == _type:
                continue
            if _filter and not passes_filter(_asset.asset, _filter):
                continue
            _item = qt.HListWidgetItem(_asset.asset)
            _item.set_data(_asset)
            widget.addItem(_item)

    def _callback__asset_filter_clear(self):
        self.ui.asset_filter.setText('')


class _HiveBroShots(object):
    """Shots tab of HiveBro."""

    ui = None
    _add_work_ctx_opts = None

    def __init__(self):
        """Constructor."""
        self._work_files = []

    def connect_signals(self):
        """Connect signals."""
        self.ui.sequence.itemSelectionChanged.connect(
            self.ui.shot.redraw)
        self.ui.shot_filter.textChanged.connect(
            self.ui.shot.redraw)

    @qt.list_redrawer
    def _redraw__sequence(self, widget):
        _seqs = tk2.obtain_sequences()
        for _seq in _seqs:
            _item = qt.HListWidgetItem(_seq.sequence)
            _item.set_data(_seq)
            widget.addItem(_item)

    @qt.list_redrawer
    def _redraw__shot(self, widget):

        _seq = get_single(self.ui.sequence.selected_data(), catch=True)
        _filter = self.ui.shot_filter.text()
        if not _seq:
            return
        _shots = _seq.find_shots(filter_=_filter)
        for _shot in _shots:
            _item = qt.HListWidgetItem(_shot.shot)
            _item.set_data(_shot)
            widget.addItem(_item)

    def _callback__shot_filter_clear(self):
        self.ui.shot_filter.setText('')


class _HiveBro(_HiveBroAssets, _HiveBroShots):
    """HiveBro interface."""

    def __init__(self):
        """Constructor."""
        _HiveBroAssets.__init__(self)
        _HiveBroShots.__init__(self)

    def connect_signals(self):
        """Connect signals."""

        _HiveBroAssets.connect_signals(self)
        _HiveBroShots.connect_signals(self)

        self.ui.main_tabs.currentChanged.connect(
            self.ui.step.redraw)
        self.ui.asset.itemSelectionChanged.connect(
            self.ui.step.redraw)
        self.ui.shot.itemSelectionChanged.connect(
            self.ui.step.redraw)

        # Step/task section
        self.ui.step.itemSelectionChanged.connect(
            self.ui.task.redraw)
        self.ui.task.itemSelectionChanged.connect(
            self.ui.task_edit.redraw)
        self.ui.task.itemSelectionChanged.connect(
            self.ui.work.redraw)
        self.ui.task_edit.textChanged.connect(
            self.ui.work.redraw)
        self.ui.task.itemSelectionChanged.connect(
            self.ui.work_save.redraw)
        self.ui.task_edit.textChanged.connect(
            self.ui.work_save.redraw)

        self.ui.work.itemSelectionChanged.connect(
            self.ui.work_open.redraw)
        self.ui.work.itemSelectionChanged.connect(
            self.ui.work_view_capture.redraw)
        self.ui.work.itemSelectionChanged.connect(
            self.ui.work_path.redraw)

    @qt.list_redrawer
    def _redraw__step(self, widget):

        # Get step root
        _mode = self.ui.main_tabs.cur_text()
        if _mode == 'Assets':
            _root = get_single(self.ui.asset.selected_data(), catch=True)
        elif _mode == 'Shots':
            _root = get_single(self.ui.shot.selected_data(), catch=True)
        else:
            raise ValueError(_mode)
        if not _root:
            return

        _sel = None
        for _step in _root.find_step_roots():
            _work_area = _step.get_work_area(dcc=_cur_dcc())
            _col = 'grey'
            if os.path.exists(_work_area.yaml):
                _col = 'white'
                _sel = _sel or _step
            _item = qt.HListWidgetItem(_step.step)
            _item.set_data(_step)
            _item.set_col(_col)
            widget.addItem(_item)

        if _sel:
            widget.select_data([_sel])

    @qt.list_redrawer
    def _redraw__task(self, widget):

        self._work_files = []
        _step = get_single(self.ui.step.selected_data(), catch=True)
        if not _step:
            return
        _work_area = _step.get_work_area(dcc=_cur_dcc())
        self._work_files = _work_area.find_work()

        # Find mtimes of latest work versions
        _tasks = sorted(set([
            _work.task for _work in self._work_files]))
        _latest_works = [
            [_work for _work in self._work_files if _work.task == _task][-1]
            for _task in _tasks]
        _mtimes = [
            _work.get_mtime() for _work in _latest_works]

        # Add to widget
        for _task, _mtime in safe_zip(_tasks, _mtimes):
            _item = qt.HListWidgetItem(_task)
            if len(set(_mtimes)) == 1:
                _col = qt.HColor('white')
            else:
                _fr = val_map(
                    _mtime, in_min=min(_mtimes), in_max=max(_mtimes))
                _col = qt.HColor('Grey').whiten(_fr)
            _item.set_col(_col)
            widget.addItem(_item)

        if _step in _tasks:
            widget.select_text([_step])

    def _redraw__task_edit(self, widget):
        _task = get_single(self.ui.task.selected_text(), catch=True)
        widget.setText(_task)

    @qt.list_redrawer
    def _redraw__work(self, widget):

        # Find work files
        _task = (
            self.ui.task_edit.text() or
            get_single(self.ui.task.selected_text(), catch=True))
        if not _task:
            return
        _work_files = [
            _work for _work in self._work_files
            if _work.task == _task]
        if not _work_files:
            return

        # Add items
        _work_data = _work_files[0].get_work_area().get_metadata()
        for _idx, _work_file in enumerate(reversed(_work_files)):
            _item = create_work_item(_work_file, data=_work_data)
            widget.addItem(_item)

    def _redraw__work_open(self, widget):
        _ver = self.ui.work.selected_data()
        widget.setEnabled(bool(_ver))

    def _redraw__work_path(self, widget):
        _work = get_single(self.ui.work.selected_data(), catch=True)
        _task = self.ui.task_edit.text()
        if not _work and _task:
            _step = get_single(self.ui.step.selected_data())
            _dcc = _cur_dcc()
            _hint = '{dcc}_{area}_work'.format(dcc=_dcc, area=_step.area)
            _work = _step.map_to(
                hint=_hint, class_=tk2.TTWork, Task=_task,
                extension=tk2.get_extn(_dcc), version=1)
        widget.setText(_work.path if _work else '')

    def _redraw__work_save(self, widget, verbose=0):

        _work_path = self.ui.work_path.text()
        _task = self.ui.task.selected_data()

        _sel_work = tk2.get_work(_work_path)
        _cur_work = tk2.cur_work()
        _text = 'Save As'
        lprint('REDRAW WORK SAVE\n - {}\n - {}'.format(_cur_work, _sel_work),
               verbose=verbose)
        if _cur_work and _sel_work:
            if _cur_work.ver_fmt == _sel_work.ver_fmt:
                _text = 'Version Up'

        widget.setEnabled(bool(_work_path))
        widget.setText(_text)

    def _redraw__work_view_capture(self, widget):
        _work = get_single(self.ui.work.selected_data(), catch=True)
        widget.setEnabled(bool(_work and _work.find_seqs()))

    def _callback__task(self):
        _task = get_single(self.ui.task.selected_text(), catch=True)
        self.ui.task_edit.setText(_task)

    def _callback__task_edit(self):
        _text = self.ui.task_edit.text()
        self.ui.task.blockSignals(True)
        if not _text:
            self.ui.task.redraw()
        elif _text in self.ui.task.all_text():
            self.ui.task.select_text(_text)
        else:
            self.ui.task.clearSelection()
        self.ui.task.blockSignals(False)

    def _callback__task_refresh(self):
        tk2.clear_caches()
        self.ui.task.redraw()

    def _callback__work_copy(self):
        _work = get_single(self.ui.work.selected_data())
        copy_text(_work.path)

    def _callback__work_open(self):
        _ver = get_single(self.ui.work.selected_data(), catch=True)
        _ver.load()
        self.ui.work_save.redraw()

    def _callback__work_jump_to(self):
        _file = host.cur_scene()
        self.select_path(_file)

    def _callback__work_refresh(self):
        _work = get_single(self.ui.work.selected_data())
        tk2.clear_caches()
        _work.find_outputs()
        self.ui.task.redraw()
        self.select_path(_work.path)

    def _callback__work_save(self):

        # Apply change task warning
        _work_path = self.ui.work_path.text()
        _cur_work = tk2.cur_work()
        _next_work = tk2.obtain_work(_work_path).find_next()
        if _cur_work:
            _cur_task = _cur_work.get_work_area(), _cur_work.task
            _next_task = _next_work.get_work_area(), _next_work.task

            print 'CUR WORK ', _cur_work
            print 'NEXT WORK', _next_work

            if _cur_task != _next_task:
                _icon = _get_work_icon(_next_work)
                qt.ok_cancel(
                    'Are you sure you want to switch to a different task?'
                    '\n\nCurrent:\n{}\n\nNew:\n{}'.format(
                        _cur_work.path, _next_work.path),
                    title='Switch task', icon=_icon)

        # Save
        _comment = qt.read_input(
            'Enter comment:', title='Save new version', parent=self)
        _next_work.save(comment=_comment)

        # Update ui
        self._callback__task_refresh()
        self._callback__work_jump_to()

    def _callback__work_view_capture(self):
        _work = get_single(self.ui.work.selected_data())
        _seq = get_single(_work.find_seqs())
        _seq.view()

    def _context__step(self, menu):
        _step = get_single(self.ui.step.selected_data(), catch=True)
        if _step:
            menu.add_action(
                'Copy path', wrap_fn(copy_text, _step.path), icon=icons.COPY)

    def _context__work(self, menu):
        _work = get_single(self.ui.work.selected_data(), catch=True)
        if _work:
            self._add_work_ctx_opts(work=_work, menu=menu)

    def _context__work_jump_to(self, menu):

        _work = get_single(self.ui.work.selected_data(), catch=True)

        # Add jump to recent options
        menu.add_label("Jump to")
        for _work in sorted(get_recent_work()):
            _work = _work.find_latest()
            if not _work:
                continue
            _label = _get_work_label(_work)
            _icon = _get_work_icon(_work, mode='basic')
            _fn = wrap_fn(self.select_path, _work.path)
            menu.add_action(_label, _fn, icon=_icon)

        menu.addSeparator()

        # Jump to clipboard work
        _clip_work = tk2.get_work(qt.get_application().clipboard().text())
        if _clip_work:
            _label = _get_work_label(_clip_work)
            _fn = wrap_fn(self.select_path, _clip_work.path)
            menu.add_action('Jump to '+_label, _fn, icon=icons.COPY)
        else:
            menu.add_label('No work in clipboard', icon=icons.COPY)

        # Add current work to recent
        if _work:
            menu.add_action(
                'Add selection to recent', _work.add_to_recent,
                icon=icons.EMOJI.find('Magnet'))

    def select_path(self, path, verbose=1):
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
            self.ui.main_tabs.setCurrentIndex(0)
        else:
            self.ui.main_tabs.setCurrentIndex(1)

        if _step:
            if not _shot:
                self.ui.asset_type.select_text([_step.sg_asset_type])
                self.ui.asset.select_text([_step.asset])
            else:
                self.ui.sequence.select_text([_step.sequence])
                self.ui.shot_filter.setText('')
                self.ui.shot.select_text([_step.shot])
            self.ui.step.select_text([_step.step])

        if _work:
            self.ui.task.select_text([_work.task])
            self.ui.work.select_data([_work])

    def _add_work_ctx_opts(self, work, menu):
        """Add context options for the given work file.

        Args:
            work (TTWork): work file
            menu (QMenu): menu to add options too
        """
        _add_path_menu_items(menu=menu, obj=work)
        menu.addSeparator()

        _set_comment_fn = chain_fns(
            wrap_fn(_set_work_comment, work, parent=self),
            wrap_fn(self._redraw__work, self.ui.work))
        menu.add_action(
            'Set comment', _set_comment_fn, icon=icons.EDIT)

        # Add output options
        self._add_work_ctx_output_files(work=work, menu=menu)

        # Add increments
        _incs = work.find_increments()
        menu.addSeparator()
        if _incs:
            _menu = menu.add_menu('Increments')
            _icon = _get_work_icon(work)
            for _inc in _incs:
                _inc_menu = _menu.add_menu(_inc.basename, icon=_icon)
                _add_path_menu_items(menu=_inc_menu, obj=_inc)
        else:
            menu.add_label('No increments found')

    def _add_work_ctx_output_files(self, work, menu):
        """Add work file output context options.

        Args:
            work (TTWork): work file
            menu (QMenu): menu to add to
        """
        _files = work.find_output_files()
        menu.addSeparator()

        # No outputs found
        if not _files:
            menu.add_label("No outputs found")
            return

        menu.add_label("Outputs")

        # Show individual files if small number
        if len(_files) < 10:
            for _file in _files:
                self._add_work_ctx_output_file(menu=menu, file_=_file)
            return

        # Organise into names
        _names = sorted(set([_file.output_name for _file in _files]))
        for _name in _names:
            _name_files = [_file for _file in _files
                           if _file.output_name == _name]
            if len(_name_files) == 1:
                self._add_work_ctx_output_file(
                    menu=menu, file_=get_single(_name_files))
            else:
                self._add_work_ctx_output_name(
                    menu=menu, name=_name, files=_name_files)

    def _add_work_ctx_output_name(self, menu, name, files):
        """Add work context options for the given output name.

        Args:
            menu (QMenu): menu to add options to
            name (TTOutputName): name to add options for
            files (TTOutputFile): files in name
        """
        _label = name.output_type
        _icon = _output_to_icon(name)
        _name_menu = menu.add_menu(_label, icon=_icon)

        for _file in files:
            self._add_work_ctx_output_file(
                menu=_name_menu, file_=_file)

    def _add_work_ctx_output_file(self, menu, file_):
        """Add work file context options for the given output.

        Args:
            menu (QMenu): menu to add to
            file_ (TTOutputFile): output file to add options for
        """
        if file_.channel:
            _label = '{} {} ({})'.format(
                file_.output_type, file_.channel, file_.format)
        else:
            _label = '{} {}/{}'.format(
                file_.output_type, file_.format, file_.extn)
        _icon = _output_to_icon(file_)
        _menu = menu.add_menu(_label, icon=_icon)
        _add_path_menu_items(menu=_menu, obj=file_)


class _HiveBroStandalone(qt.HUiDialog2, _HiveBro):
    """HiveBro interface as a standalone dialog (rather than docked)."""

    def __init__(self):
        """Constructor."""
        _HiveBro.__init__(self)
        super(_HiveBroStandalone, self).__init__(ui_file=UI_FILE)
        self.connect_signals()
        self.set_icon(icons.EMOJI.find('Honeybee'))
        if not host.NAME == 'maya':
            qt.set_maya_palette()
        self.ui.show()


def _add_path_menu_items(menu, obj):
    """Add menu items for the given path object.

    Args:
        menu (QMenu): menu to add items to
        obj (Path): path object
    """

    # Add label
    if isinstance(obj, Seq):
        _start, _end = obj.find_range()
        _join = '...' if obj.has_missing_frames() else '-'
        _label = 'Seq {:d}{}{:d}'.format(_start, _join, _end)
    else:
        _label = 'File'
    menu.add_label(_label)

    menu.add_action(
        'Copy path', wrap_fn(copy_text, obj.path),
        icon=icons.COPY)

    _browser = wrap_fn(launch_browser, obj.dir)
    menu.add_action(
        'Show in explorer', _browser, icon=icons.BROWSER)

    if obj.extn in ['mb', 'ma', 'abc']:

        # Open scene
        _open = wrap_fn(host.open_scene, obj.path)
        menu.add_action('Open scene', _open, icon=icons.OPEN)

        # Reference scene
        _namespace = obj.basename
        if isinstance(obj, tk2.TTWork):
            _namespace = obj.task
        elif isinstance(obj, tk2.TTOutputFile):
            _namespace = obj.output_name
        _ref = wrap_fn(host.reference_scene, obj.path, namespace=_namespace)
        _pix = qt.HPixmap(icons.OPEN)
        _pix.add_overlay(
            icons.EMOJI.find('Diamond With a Dot'),
            pos=_pix.size(), resize=80, anchor='BR')
        menu.add_action('Reference scene', _ref, icon=_pix)

        # Reference asset
        if isinstance(obj, tk2.TTOutputFile):
            _fn = wrap_fn(tk2.reference_publish, obj.path)
            menu.add_action('Reference publish', _fn, icon=_pix)

    if isinstance(obj, Seq):
        _icon = icons.EMOJI.find('Play button')
        menu.add_action('View images', obj.view, icon=_icon)
    elif obj.extn == 'mov':
        _icon = icons.EMOJI.find('Play button')
        _view = wrap_fn(system, 'djv_view '+obj.path)
        menu.add_action('View images', _view, icon=_icon)


def create_work_item(work, data=None):
    """Create work list widget item.

    Args:
        work (TTWork): work to build item from
        data (dict): work metadata

    Returns:
        (HListWidgetItem): list widget item for this work file
    """
    _icon = _get_work_icon(work)
    _text = _get_work_text(work, data=data)
    _col = _get_work_col(work)
    _item = qt.HListWidgetItem(_text)
    if _col:
        _item.set_col(_col)
    _item.set_data(work)
    _item.set_icon(_icon)

    return _item


def _cur_dcc():
    """Get current dcc name (using tank template naming).

    Returns:
        (str): dcc name
    """
    return {'hou': 'houdini'}.get(host.NAME, host.NAME)


def get_recent_work(verbose=0):
    """Read list of recent work file from tank.

    Args:
        verbose (int): print process data

    Returns:
        (TTWork list): list of work files
    """
    _settings = QtCore.QSettings('Sgtk', 'psy-multi-fileops')
    _setting_name = '{}/recent_files'.format(pipe.cur_project().name)
    _works = []
    for _file in _settings.value(_setting_name, []):
        _path = abs_path(_file['file_path'])
        lprint('TESTING', _path, verbose=verbose)
        _work = tk2.obtain_work(_path)
        if not _work:
            continue
        if not _work.dcc == _cur_dcc():
            continue
        _works.append(_work)
    return _works


def _get_work_col(work):
    """Get colour for work file list item.

    Args:
        work (CTTWork): work file to test

    Returns:
        (str|None): colour for work file
    """
    if work.find_publishes():
        return 'DodgerBlue'
    elif work.find_caches():
        return 'Aquamarine'
    elif work.find_seqs():
        return 'DeepSkyBlue'
    return None


@store_result_on_obj
def _get_work_icon(
        work, mode='full', size=50, overlay_size=25,
        force=False, verbose=0):
    """Get icon for the given work file.

    Args:
        work (CTTWork): work file
        mode (str): type of icon to build (full/basic)
        size (int): icon size
        overlay_size (int): overlay size
        force (bool): force redraw icon
        verbose (int): print process data

    Returns:
        (str|QPixmap): work file icon
    """

    # Get base icon
    _uid = work.task
    lprint('UID', _uid, verbose=verbose)
    if _uid == 'test':
        _icon = icons.EMOJI.find('Alembic')
    else:
        _random = str_to_seed(_uid)
        _icon = _random.choice(icons.FRUIT.get_paths())
    lprint('ICON', _icon, verbose=verbose)
    if mode == 'basic':
        return _icon

    _random = str_to_seed(work.path)
    _rotate = _random.random()*360

    _pix = qt.HPixmap(size, size)
    _pix.fill(qt.HColor(0, 0, 0, 0))

    # Add rotated icon as overlay
    _size_fr = 1 / (2**0.5)
    _size = _pix.size()*_size_fr
    _over = qt.HPixmap(_icon).resize(_size)
    _tfm = QtGui.QTransform()
    _tfm.rotate(_rotate)
    _over = _over.transformed(_tfm)
    _offs = (_pix.size() - _over.size())/2
    _pix.add_overlay(_over, _offs)

    # Add overlays
    _overlays = []
    if work.find_seqs():
        _over = qt.HPixmap(icons.EMOJI.find('Play button')).resize(
            overlay_size)
        _overlays.append(_over)
    if work.find_publishes():
        _over = qt.HPixmap(icons.EMOJI.find('Funeral Urn')).resize(
            overlay_size)
        _overlays.append(_over)
    if work.find_caches():
        _over = qt.HPixmap(icons.EMOJI.find('Money bag')).resize(
            overlay_size)
        _overlays.append(_over)
    # for _idx, _over in reversed(list(enumerate(_overlays))):
    for _idx, _over in enumerate(_overlays):
        _offs = (13*_idx, _pix.height()-0*_idx)
        lprint(' - ADD OVERLAY', _idx, _offs, verbose=verbose)
        _pix.add_overlay(_over, _offs, anchor='BL')

    return _pix


def _get_work_label(work):
    """Get context menu label for work file.

    Args:
        work (TTWork): work file

    Returns:
        (str): label
    """
    if work.shot:
        _label = '{}/{}/{}'.format(work.shot, work.step, work.task)
    else:
        _label = '{}/{}/{}'.format(work.asset, work.step, work.task)
    return _label


def _get_work_text(work, data=None):
    """Get display text for the given work file.

    Args:
        work (TTWork): work file
        data (dict): version data

    Returns:
        (str): display text
    """
    _data = work.get_metadata(data=data)
    if not _data:
        _mtime = get_time_t(os.path.getmtime(work.path))
        _owner = get_owner(work.path) or '-'
        _comment = '<Missing from metadata>'
    else:
        _fmt = '%d %b %Y %H:%M:%S'
        _mtime = time.strptime(_data['created'], _fmt)
        _comment = (_data.get('comment') or '').replace(
            'Versioned up for publish: ', '') or '-'
        _owner = _data['owner']

    _text = 'v{:03d} - {}'.format(
        work.version, time.strftime('%a %d/%m/%y %H:%M:%S', _mtime))
    _text += '\n - Comment: '+_comment
    _text += '\n - Owner: '+_owner

    if work.find_captures():
        _text += '\n - Captured'
    if work.find_renders():
        _text += '\n - Rendered'
    if work.find_publishes():
        _text += '\n - Published'
    if work.find_caches():
        _text += '\n - Cached'

    return _text


@store_result
def _output_to_icon(output):
    """Get icon for the given output.

    Args:
        output (TTOutput): output to get icon for

    Returns:
        (str): path to icon
    """
    _name = None
    if hasattr(output, 'extn'):
        if output.extn == 'abc':
            _name = 'Input Latin Letters'
        elif output.extn in ['ma', 'mb']:
            _name = 'Moai'

    if not _name:
        _name = {
            'fxcache': 'Collision',
            'capture': 'Play Button',
            'render': 'Play Button',
            'animcache': 'Money Bag',
            'camcache': 'Movie Camera',
            'shadegeo': 'Bust in Silhouette',
        }.get(output.output_type, 'Blue Circle')

    return icons.EMOJI.find(_name)


def _set_work_comment(ver, parent):
    """Set comment for the given work file.

    Args:
        ver (TTWork): work file to set comment on
        parent (QDialog): parent dialog
    """
    _comment = qt.read_input(
        msg='Please enter new comment for {} v{:03d}:'.format(
            ver.task, ver.version),
        title='Enter comment', parent=parent, default=ver.get_comment())
    ver.set_comment(_comment)


def launch(path=None):
    """Launch HiveBro interface.

    Args:
        path (str): apply path on launch

    Returns:
        (HiveBro): hive bro instance
    """
    from psyhive.tools import hive_bro

    tk2.clear_caches()

    print 'Launching HiveBro'
    _dialog = _HiveBroStandalone()
    hive_bro.DIALOG = _dialog

    # Select path
    _path = path
    if not _path:
        _path = host.cur_scene()
    if not _path:
        _recent = get_recent_work()
        if _recent:
            _path = _recent[0].path
    if _path:
        _dialog.select_path(_path)

    return _dialog
