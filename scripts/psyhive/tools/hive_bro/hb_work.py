"""Tools for HiveBro relating to work items."""

import os
import time

from psyhive import qt, icons, host, pipe, tk2
from psyhive.qt import QtCore, QtGui
from psyhive.utils import (
    get_single, wrap_fn, abs_path, store_result, system,
    get_time_t, get_owner, chain_fns, lprint, copy_text,
    str_to_seed, launch_browser, Seq)

from . import hb_utils


def get_work_ctx_opts(work, menu, redraw_work, parent):
    """Add context options for the given work file.

    Args:
        work (TTWork): work file
        menu (QMenu): menu to add options too
        redraw_work (fn): function for redrawing work items
        parent (QDialog): parent dialog
    """
    _add_path_menu_items(menu=menu, obj=work)
    menu.addSeparator()

    _set_comment_fn = chain_fns(
        wrap_fn(_set_work_comment, work, parent=parent),
        redraw_work)
    menu.add_action(
        'Set comment', _set_comment_fn, icon=icons.EDIT)

    # Add output options
    _add_work_ctx_output_files(work=work, menu=menu)

    # Add increments
    _incs = work.find_incs()
    menu.addSeparator()
    if _incs:
        _menu = menu.add_menu('Increments')
        _icon = get_work_icon(work)
        for _inc in _incs:
            _inc_menu = _menu.add_menu(_inc.basename, icon=_icon)
            _add_path_menu_items(menu=_inc_menu, obj=_inc)
    else:
        menu.add_label('No increments found')


def _add_work_ctx_output_files(work, menu):
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
            _add_work_ctx_output_file(menu=menu, file_=_file)
        return

    # Organise into names
    _names = sorted(set([_file.output_name for _file in _files]))
    for _name in _names:
        _name_files = [_file for _file in _files
                       if _file.output_name == _name]
        if len(_name_files) == 1:
            _add_work_ctx_output_file(
                menu=menu, file_=get_single(_name_files))
        else:
            _add_work_ctx_output_name(
                menu=menu, name=_name, files=_name_files)


def _add_work_ctx_output_name(menu, name, files):
    """Add work context options for the given output name.

    Args:
        menu (QMenu): menu to add options to
        name (TTOutputName): name to add options for
        files (TTOutputFile): files in name
    """
    _icon = _output_to_icon(files[0])
    _name_menu = menu.add_menu(name, icon=_icon)

    for _file in files:
        _add_work_ctx_output_file(
            menu=_name_menu, file_=_file)


def _add_work_ctx_output_file(menu, file_):
    """Add work file context options for the given output.

    Args:
        menu (QMenu): menu to add to
        file_ (TTOutputFile): output file to add options for
    """
    if file_.channel:
        _label_fmt = '{output_type} {channel} ({format})'
    else:
        _label_fmt = '{output_type} {output_name} ({format}/{extension})'
    _label = _label_fmt.format(**file_.data)
    _icon = _output_to_icon(file_)
    _menu = menu.add_menu(_label, icon=_icon)
    _add_path_menu_items(menu=_menu, obj=file_)


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
    _icon = get_work_icon(work)
    _text = _get_work_text(work, data=data)
    _col = _get_work_col(work)
    _item = qt.HListWidgetItem(_text)
    if _col:
        _item.set_col(_col)
    _item.set_data(work)
    _item.set_icon(_icon)

    return _item


def get_recent_work(verbose=0):
    """Read list of recent work file from tank.

    Args:
        verbose (int): print process data

    Returns:
        (TTWork list): list of work files
    """
    _settings = QtCore.QSettings('Sgtk', 'psy-multi-fileops')
    lprint('READING SETTINGS', _settings.fileName(), verbose=verbose)
    _setting_name = '{}/recent_files'.format(pipe.cur_project().name)
    _works = []
    for _file in _settings.value(_setting_name, []):
        _path = abs_path(_file['file_path'])
        lprint('TESTING', _path, verbose=verbose)
        _work = tk2.obtain_work(_path)
        if not _work:
            continue
        if not _work.dcc == hb_utils.cur_dcc():
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


@store_result
def get_work_icon(
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
    for _idx, _over in enumerate(_overlays):
        _offs = (13*_idx, _pix.height()-0*_idx)
        lprint(' - ADD OVERLAY', _idx, _offs, verbose=verbose)
        _pix.add_overlay(_over, _offs, anchor='BL')

    return _pix


def get_work_label(work):
    """Get context menu label for work file.

    Args:
        work (TTWork): work file

    Returns:
        (str): label
    """
    if work.shot:
        _label = '{}/{}/{}'.format(work.shot, work.step, work.task)
    else:
        _label = 'assets/{}/{}/{}'.format(work.asset, work.step, work.task)
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

    # Label outputs
    _outs = set(work.find_outputs())
    for _fn, _label in [
            (work.find_captures, 'Captured'),
            (work.find_renders, 'Rendered'),
            (work.find_publishes, 'Published'),
            (work.find_caches, 'Cached')]:
        _results = set(_fn())
        if _results:
            _outs -= _results
            _text += '\n - '+_label
    if _outs:
        _text += '\n - Outputs'

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
