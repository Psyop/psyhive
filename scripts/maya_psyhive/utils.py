"""General utilties for maya."""

import functools

from maya import cmds

COLS = (
    "deepblue", "black", "darkgrey", "grey", "darkred", "darkblue", "blue",
    "darkgreen", "deepgrey", "magenta", "brown", "deepbrown", "redbrown",
    "red", "green", "fadedblue", "white", "yellow", "lightblue", "lightgreen",
    "pink", "orange", "lightyellow", "fadedgreen", "darktan", "tanyellow",
    "olivegreen", "woodgreen", "cyan", "greyblue", "purple", "crimson")


def get_unique(name):
    """Get unique version of the given node name.

    This is strip any trailing digits from the name provided, and then
    find the first available index which will avoid a name clash.

    Args:
        name (str): node name to check

    Returns:
        (str): unique node name
    """
    _clean_name = str(name).split("|")[-1].split(":")[-1]
    _cur_ns = cmds.namespaceInfo(currentNamespace=True).rstrip(":")
    _trg_node = "%s:%s" % (_cur_ns, _clean_name)

    if cmds.objExists(_trg_node):

        # Strip digits from clean name
        for _ in range(len(_clean_name)):
            if not _clean_name[-1].isdigit():
                break
            _clean_name = _clean_name[: -1]
        _trg_node = "%s:%s" % (_cur_ns, _clean_name)

        if cmds.objExists(_trg_node):

            # Inc digits until unique name
            _idx = 1
            while True:
                _trg_node = "%s:%s%d" % (_cur_ns, _clean_name, _idx)
                if not cmds.objExists(_trg_node):
                    break
                _idx += 1

            _clean_name = "%s%d" % (_clean_name, _idx)

    return _clean_name


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
            set_namespace(namespace, clean=True)
            _result = func(*args, **kwargs)
            set_namespace(":")
            return _result

        return _ns_clean_fn

    return _ns_cleaner


def restore_sel(func):
    """Decorator which restores current selection after exection.

    Args:
        func (fn): function to decorate
    """

    @functools.wraps(func)
    def _restore_sel_fn(*args, **kwargs):
        _sel = cmds.ls(selection=True)
        _result = func(*args, **kwargs)
        cmds.select(_sel)
        return _result

    return _restore_sel_fn


def set_col(node, col):
    """Set viewport colour of the given node.

    Args:
        node (str): node to change colour of
        col (str): colour to apply
    """
    if col not in COLS:
        raise ValueError(
            "Col {} not in colour list: {}".format(col, COLS))
    cmds.setAttr(node+'.overrideEnabled', 1)
    cmds.setAttr(node+'.overrideColor', COLS.index(col))


def set_namespace(namespace, clean=False):
    """Set current namespace, creating it if required.

    Args:
        namespace (str): namespace to apply
        clean (bool): delete all nodes in this namespace
    """
    _namespace = namespace
    assert _namespace.startswith(':')

    if clean:
        _nodes = cmds.ls(_namespace+":*")
        if _nodes:
            cmds.delete(_nodes)

    if not cmds.namespace(exists=_namespace):
        cmds.namespace(addNamespace=_namespace)
    cmds.namespace(setNamespace=_namespace)


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


def use_tmp_ns(func):
    """Decorator which executes function in a temporary namespace.

    Args:
        func (fn): function to execute

    Returns:
        (fn): decorated function
    """
    return get_ns_cleaner(':tmp')(func)
