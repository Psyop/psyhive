"""Tools for batch submitting rerenders."""

import copy

from maya import cmds

from psyq.jobs.maya import render_settings, hooks, render_job

from psyhive import tk, qt, host
from psyhive.utils import get_plural, get_single
from maya_psyhive import ref
from maya_psyhive import open_maya as hom


def rerender_work_file(work_file, passes, range_):
    """Rerender a work file.

    Assets are updated to the latest version and then the workfile is
    versioned up.

    Args:
        work_file (TTWorkFileBase): work file to rerender
        passes (str list): list of passes to rerender
        range_ (int tuple): start/end frames

    Returns:
        (tuple): layers which were missing from the scene
    """
    _work = work_file.find_latest()
    _layers = [_layer_from_pass(_pass) for _pass in passes]
    print 'RERENDERING', _work
    if not host.cur_scene() == _work.path:
        _work.load(force=True)
    print ' - SCENE IS LOADED'

    # Check for missing layers
    _missing_layers = []
    for _layer in copy.copy(_layers):
        if not cmds.objExists(_layer):
            _missing_layers.append(_layer)
            _layers.remove(_layer)
    if _missing_layers:
        print 'MISSING LAYERS', _missing_layers
    if not _layers:
        raise RuntimeError("No layers were found to render")
    print ' - FOUND LAYERS TO RENDER', _layers

    _update_outputs_to_latest()

    _next_work = _work.find_next()
    _next_work.save(comment="Version up for batch rerender")

    _submit_render(
        file_=_next_work.path, layers=_layers, force=True,
        range_=range_)

    return _missing_layers


def _layer_from_pass(pass_):
    """Get render layer name from pass name.

    Args:
        pass_ (str): pass name

    Returns:
        (str): render layer name
    """
    if pass_ == 'masterLayer':
        return 'defaultRenderLayer'
    return 'rs_{}'.format(pass_)


def _update_outputs_to_latest():
    """Update outputs referenced in this file to latest versions."""

    for _ref in ref.find_refs():

        # Find asset
        _asset = tk.get_output(_ref.path)
        if not _asset:
            continue

        print 'CHECKING ASSET', _ref

        # Make sure asset is latest
        if not _asset.is_latest():
            _latest = _asset.find_latest()
            print ' - UPDATING TO LATEST: {}'.format(_latest.path)

            _ref.swap_to(_latest.path)

        # Check if cache needs updating
        _exo = get_single([
            _node for _node in hom.CMDS.referenceQuery(
                _ref.ref_node, nodes=True)
            if cmds.objectType(_node) == 'ExocortexAlembicFile'], catch=True)
        if _exo:
            print ' - EXO', _exo
            _abc = _exo.plug('fileName').get_val()
            print ' - CURRENT ABC', _abc
            _output = tk.get_output(_abc)
            if _output and not _output.is_latest():
                _latest = _output.find_latest()
                print ' - UPDATING TO LATEST', _latest
                _exo.plug('fileName').set_val(_latest.path)
            else:
                print ' - IS LATEST'


def _submit_render(file_, layers, range_, force=False):
    """Submit render.

    This doesn't handle opening the scene and updating the assets.

    Args:
        file_ (str): path to scene to submit
        layers (list): layers to submit
        range_ (int tuple): start/end frames
        force (bool): submit with no confirmation
    """
    _start, _end = range_
    _settings = render_settings.RenderSubmitSettings()
    _settings.render_layers = layers
    _settings.render_layer_mode = render_job.RenderLayerMode.CUSTOM
    _settings.range_start = _start
    _settings.range_end = _end
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
