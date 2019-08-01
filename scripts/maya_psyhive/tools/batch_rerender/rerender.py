"""Tools for batch submitting rerenders."""

import copy
import pprint

from maya import cmds

from psyq.jobs.maya import render_settings, hooks, render_job

from psyhive import tk, qt, host
from psyhive.utils import get_plural
from maya_psyhive import ref


def rerender_work_files(work_files, passes):
    """Rerender the given list of work files.

    Args:
        work_files (TTWorkFileBase list): work files to rerender
        passes (str list): list of passes to rerender
    """
    qt.ok_cancel(
        'Are you sure you want to rerender {:d} passes in {:d} '
        'work files?'.format(len(passes), len(work_files)))

    _missing_layers = []
    for _work_file in qt.ProgressBar(
            work_files, 'Re-rendering {:d} work file{}'):
        _work_file = tk.get_work(_work_file.path)  # Don't want cacheable
        _file_missing_layers = _rerender_work_file(_work_file, passes)
        if _file_missing_layers:
            _missing_layers.append([_work_file, _missing_layers])

    if _missing_layers:
        print 'MISSING LAYERS'
        pprint.pprint(_missing_layers)
        qt.notify_warning(
            'Some passes were not found in the work file.\n\n'
            'Check the script editor for details.')
    else:
        qt.notify('{:d} passes submitted to the farm.'.format(len(passes)))


def _rerender_work_file(work_file, passes):
    """Rerender a work file.

    Assets are updated to the latest version and then the workfile is
    versioned up.

    Args:
        work_file (TTWorkFileBase): work file to rerender
        passes (str list): list of passes to rerender

    Returns:
        (tuple): layers which were missing from the scene
    """
    _work = work_file.find_latest()
    _layers = ['rs_{}'.format(_pass) for _pass in passes]
    print _work
    if not host.cur_scene() == _work.path:
        _work.load()

    # Check for missing layers
    _missing_layers = []
    for _layer in copy.copy(_layers):
        if not cmds.objExists(_layer):
            _missing_layers.append(_layer)
            _layers.remove(_layer)
    if _missing_layers:
        print 'MISSING LAYERS', _missing_layers
    if not _layers:
        return _missing_layers

    # Update assets
    for _ref in ref.find_refs():
        _asset = tk.get_output(_ref.path)
        if not _asset:
            continue
        if not _asset.is_latest():
            _latest = _asset.find_latest()
            print 'UPDATING {} TO LATEST: {}'.format(
                _ref.namespace, _latest.path)
            _ref.swap_to(_latest.path)

    _next_work = _work.find_next()
    _next_work.save(comment="Version up for batch rerender")

    _submit_render(file_=_next_work.path, layers=_layers, force=True)

    return _missing_layers


def _submit_render(file_, layers, force=False):
    """Submit render.

    This doesn't handle opening the scene and updating the assets.

    Args:
        file_ (str): path to scene to submit
        layers (list): layers to submit
        force (bool): submit with no confirmation
    """
    _settings = render_settings.RenderSubmitSettings()
    _settings.render_layers = layers
    _settings.render_layer_mode = render_job.RenderLayerMode.CUSTOM
    _settings.range_start = host.t_start()
    _settings.range_end = host.t_end()
    _settings.frame_source = render_job.FrameSource.FRAME_RANGE

    _render_job = render_job.MayaRenderJob(
        settings=_settings, scene_path=file_)

    print 'RENDER JOB', _render_job
    print 'LAYERS', _render_job.render_layers
    print 'SCENE PATH', _render_job.scene_path
    print 'FRAMES', _render_job.frames
    _submittable = hooks.default_get_render_submittable_hook(_render_job)
    print 'SUBMITTABLE', _submittable

    if not force:
        qt.ok_cancel('Submit?')
    _submitted = hooks.QubeSubmitter().submit(_submittable)
    if _submitted:
        print 'Successfully submitted {:d} job{} to the farm.'.format(
            len(_submitted), get_plural(_submitted))
