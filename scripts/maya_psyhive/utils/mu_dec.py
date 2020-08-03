"""Decorators for maya."""

import functools
import os
import traceback

from maya import cmds

from psyhive.utils import lprint


def get_ns_cleaner(namespace):
    """Build a decorator that executes a function in a cleaned namespace.

    This will empty the given namespace before executing the function,
    and then revert to the root namespace after execution.

    Args:
        namespace (str): namespace to use during execution

    Returns:
        (fn): decorator
    """

    def _ns_cleaner(func):

        @functools.wraps(func)
        def _ns_clean_fn(*args, **kwargs):
            from .mu_tools import set_namespace
            set_namespace(namespace, clean=True)
            _result = func(*args, **kwargs)
            set_namespace(":")
            return _result

        return _ns_clean_fn

    return _ns_cleaner


def freeze_viewports_on_exec(func, verbose=0):
    """Decorator to freeze viewports on execute.

    Viewports are frozen before execute and then unfrozen on completion.
    If an error occurs, it's caught, the viewports are unfrozen, and the
    the exception is raised.

    Args:
        func (fn): function to decorate
        verbose (int): print process data

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _freeze_viewport_fn(*arg, **kwargs):
        if (
                os.environ.get('PSYHIVE_DISABLE_FREEZE_VIEWPORTS') or
                cmds.about(batch=True)):
            return func(*arg, **kwargs)

        # Freeze panels
        _panels = cmds.getPanel(type='modelPanel') or []
        for _panel in _panels:
            cmds.isolateSelect(_panel, state=True)

        # Run the function
        _exc = None
        try:
            _result = func(*arg, **kwargs)
        except Exception as _exc:
            _traceback = traceback.format_exc().strip()
            lprint('TRACEBACK', _traceback, verbose=verbose)

        # Unfreeze panels
        for _panel in _panels:
            cmds.isolateSelect(_panel, state=False)

        if _exc:
            raise _exc

        return _result

    return _freeze_viewport_fn


def pause_viewports_on_exec(func):
    """Pause viewports on execute function and the unpause.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _pause_viewport_func(*args, **kwargs):
        from .mu_tools import pause_viewports
        pause_viewports(True)
        _result = func(*args, **kwargs)
        pause_viewports(False)
        return _result

    return _pause_viewport_func


def restore_frame(func):
    """Decorator to execute a function, restoring the original frame.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _restore_frame_fn(*args, **kwargs):
        _frame = cmds.currentTime(query=True)
        _result = func(*args, **kwargs)
        cmds.currentTime(_frame)
        return _result

    return _restore_frame_fn


def restore_ns(func):
    """Decorator to execute a function, restoring the original namespace.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _restore_ns_fn(*args, **kwargs):
        _ns = ':'+cmds.namespaceInfo(currentNamespace=True)
        _result = func(*args, **kwargs)
        if cmds.namespace(exists=_ns):
            cmds.namespace(set=_ns)
        return _result

    return _restore_ns_fn


def reset_ns(func):
    """Decorator to execute a function, restoring the original namespace.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _reset_ns_fn(*args, **kwargs):
        _result = func(*args, **kwargs)
        cmds.namespace(set=':')
        return _result

    return _reset_ns_fn


def restore_sel(func):
    """Decorator which restores current selection after exection.

    Args:
        func (fn): function to decorate
    """

    @functools.wraps(func)
    def _restore_sel_fn(*args, **kwargs):
        _sel = cmds.ls(selection=True)
        _result = func(*args, **kwargs)
        _sel = [_node for _node in _sel if cmds.objExists(_node)]
        if _sel:
            cmds.select(_sel)
        return _result

    return _restore_sel_fn


def single_undo(func):
    """Decorator to make a function only occuy one place in the undo list.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    @functools.wraps(func)
    def _single_undo_fn(*args, **kwargs):
        cmds.undoInfo(openChunk=True)
        _result = func(*args, **kwargs)
        cmds.undoInfo(closeChunk=True)
        return _result

    return _single_undo_fn
