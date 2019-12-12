"""General utilties for maya."""

import functools
import os
import traceback

from maya import cmds
import six

from psyhive import qt
from psyhive.utils import get_single, lprint, test_path

COLS = (
    "deepblue", "black", "darkgrey", "grey", "darkred", "darkblue", "blue",
    "darkgreen", "deepgrey", "magenta", "brown", "deepbrown", "redbrown",
    "red", "green", "fadedblue", "white", "yellow", "lightblue", "lightgreen",
    "pink", "orange", "lightyellow", "fadedgreen", "darktan", "tanyellow",
    "olivegreen", "woodgreen", "cyan", "greyblue", "purple", "crimson")

_FPS_LOOKUP = {
    23.97: "film",
    23.98: "film",
    24.0: "film",
    25.0: "pal",
    29.97: "ntsc",
    30.0: "ntsc",
    48.0: "show",
    50.0: "palf",
    60.0: "ntscf"}


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


def add_node(input1, input2, output=None, name='add', force=False):
    """Create an add node.

    Args:
        input1 (str|HPlug): first input
        input2 (str|HPlug|float): second input or value
        output (str|HPlug): output
        name (str): node name
        force (bool): force replace any existing connection on output

    Returns:
        (str): add node name
    """
    from maya_psyhive import open_maya as hom

    # Create node
    _add = cmds.createNode('plusMinusAverage', name=name)

    # Connect input 1
    cmds.connectAttr(input1, _add+'.input1D[0]')

    # Connect/set input 2
    _connect_types = tuple(list(six.string_types)+[hom.HPlug])
    if isinstance(input2, _connect_types):
        cmds.connectAttr(input2, _add+'.input1D[1]')
    else:
        cmds.setAttr(_add+'.input1D[1]', input2)

    # Connect output
    _output = _add+'.output1D'
    if output:
        cmds.connectAttr(_output, output, force=force)

    return _output


def create_attr(attr, value, keyable=True, update=True, verbose=0):
    """Add an attribute.

    Args:
        attr (str): attr name (eg. persp1.blah)
        value (any): attribute value to apply
        keyable (bool): keyable state of attribute
        update (bool): update attribute to value provided
            (default is true)
        verbose (int): print process data

    Returns:
        (str): full attribute name (eg. persp.blah)
    """
    _node, _attr = attr.split('.')

    # Create attr
    _type = _class = None
    _created = False
    if not cmds.attributeQuery(_attr, node=_node, exists=True):
        if isinstance(value, qt.HColor):
            cmds.addAttr(
                _node, longName=_attr, attributeType='float3',
                usedAsColor=True)
            for _chan in 'RGB':
                print 'ADDING', _attr+_chan
                cmds.addAttr(
                    _node, longName=_attr+_chan, attributeType='float',
                    parent=_attr)
            _class = qt.HColor
        else:
            _kwargs = {
                'longName': _attr,
                'keyable': keyable,
            }
            if isinstance(value, six.string_types):
                _kwargs['dataType'] = 'string'
                _type = 'string'
            elif isinstance(value, float):
                _kwargs['attributeType'] = 'float'
                _kwargs['defaultValue'] = value
            elif isinstance(value, int):
                _kwargs['attributeType'] = 'long'
                _kwargs['defaultValue'] = value
            else:
                raise ValueError(value)
            lprint("ADDING ATTR", _node, _kwargs, verbose=verbose)
            cmds.addAttr(_node, **_kwargs)
        _created = True

    # Apply value
    _cur_val = get_val(attr, type_=_type, class_=_class)
    if not _cur_val == value and (_created or update):
        _kwargs = {}
        set_val(attr, value)

    return attr


@restore_ns
def add_to_grp(obj, grp):
    """Add the given object to the given group, creating it if required.

    Args:
        obj (str): object to add
        grp (str): name of group to add to
    """
    if not cmds.objExists(grp):
        cmds.namespace(set=':')
        cmds.group(name=grp, empty=True)
    cmds.parent(obj, grp)
    return grp


@restore_ns
def add_to_set(obj, set_, verbose=0):
    """Add the given object to the given set, creating it if required.

    Args:
        obj (str): object to add
        set_ (str): name of set to add to
        verbose (int): print process data
    """
    if not cmds.objExists(set_):
        lprint("SET DOES NOT EXIST:", set_, verbose=verbose)
        cmds.namespace(set=':')
        cmds.sets(name=set_, empty=True)
    cmds.sets(obj, addElement=set_)


def break_conns(attr):
    """Break connections on the given attribute.

    Args:
        attr (str): name of attribute
    """
    _conns = cmds.listConnections(attr, destination=False)
    cmds.delete(_conns)


def cycle_check():
    """Check cycle check is disabled.

    Provided to avoid straight turning it off, which can be expensive.
    """
    if cmds.cycleCheck(query=True, evaluation=True):
        cmds.cycleCheck(evaluation=False)


@restore_ns
def del_namespace(namespace):
    """Delete the given namespace.

    Args:
        namespace (str): namespace to delete
    """
    set_namespace(namespace, clean=True)
    set_namespace(":")
    cmds.namespace(removeNamespace=namespace)


def divide_node(input1, input2, output=None, force=False, name='divide'):
    """Create a divide node and use it to perform attr maths.

    Args:
        input1 (str): first input
        input2 (str|float): second input (or divide value)
        output (str): output node
        force (bool): force connect output (avoid already
            connected error)
        name (str): override node name

    Returns:
        (str): output attr
    """
    from maya_psyhive import open_maya as hom

    # Create node
    _div = cmds.createNode('multiplyDivide', name=name)
    for _axis in 'YZ':
        for _input in [1, 2]:
            _attr = '{}.input{:d}{}'.format(_div, _input, _axis)
            cmds.setAttr(_attr, keyable=False)
    cmds.setAttr(_div+'.operation', 2)

    # Connect input 1
    cmds.connectAttr(input1, _div+'.input1X')

    # Connect/set input 2
    _connect_types = tuple(list(six.string_types)+[hom.HPlug])
    if isinstance(input2, _connect_types):
        cmds.connectAttr(input2, _div+'.input2X')
    else:
        cmds.setAttr(_div+'.input2X', input2)

    # Connect output
    _output = _div+'.outputX'
    if output:
        cmds.connectAttr(_output, output, force=force)

    return _output


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


def get_fps():
    """Get current frame rate.

    Returns:
        (float): fps
    """
    _unit = cmds.currentUnit(query=True, time=True)

    for _fps, _name in reversed(_FPS_LOOKUP.items()):
        if _fps in [23.98, 23.97, 29.97]:  # Ignore values that confuse maya
            continue
        if _unit == _name:
            return _fps

    try:
        return float(_unit.replace("fps", ""))
    except ValueError:
        pass

    raise RuntimeError("Unknown maya time unit: "+_unit)


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


def get_parent(node):
    """Get parent of the given node.

    Args:
        node (str): node to read

    Returns:
        (str): parent node
    """
    _parents = cmds.listRelatives(node, parent=True, path=True) or []
    return get_single(_parents, catch=True)


def get_shp(node, verbose=0):
    """Get the shape of the given node.

    Args:
        node (str): node to read
        verbose (int): print process data

    Returns:
        (str): shape node
    """
    _shps = cmds.listRelatives(node, shapes=True, noIntermediate=True)
    lprint('SHAPES', _shps, verbose=verbose)
    if not len(_shps) == 1:
        raise ValueError("Multiple shapes found on {} - {}".format(
            node, ', '.join(_shps)))
    return get_single(_shps)


def get_val(attr, type_=None, class_=None, verbose=0):
    """Read an attribute value.

    This handles different attribute types without requiring extra flags.
    For example, a string attr will be read as a string.

    Args:
        attr (str): attr to read
        type_ (str): attribute type name (if known)
        class_ (any): cast result to this type
        verbose (int): print process data

    Returns:
        (any): attribute value
    """
    _node, _attr = attr.split('.')
    _type = type_ or cmds.attributeQuery(_attr, node=_node, attributeType=True)

    _kwargs = {}
    if _type in ('typed', 'string'):
        _kwargs['asString'] = True
    elif _type in ['float', 'long', 'doubleLinear', 'float3', 'double',
                   'double3', 'time', 'byte', 'bool', 'int']:
        pass
    else:
        raise ValueError('Unhandled type {} on attr {}'.format(_type, attr))

    _result = cmds.getAttr(attr, **_kwargs)
    lprint('RESULT:', _result, verbose=verbose)
    if class_:
        if class_ is qt.HColor:
            _result = class_(*get_single(_result))
        else:
            _result = class_(_result)
    return _result


def get_unique(name, verbose=0):
    """Get unique version of the given node name.

    This is strip any trailing digits from the name provided, and then
    find the first available index which will avoid a name clash.

    Args:
        name (str): node name to check
        verbose (int): print process data

    Returns:
        (str): unique node name
    """
    _clean_name = str(name).split("|")[-1].split(":")[-1]
    _cur_ns = cmds.namespaceInfo(currentNamespace=True).rstrip(":")
    _trg_node = "%s:%s" % (_cur_ns, _clean_name) if _cur_ns else _clean_name
    lprint('NODE EXISTS:', _trg_node, verbose=verbose)

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


def is_visible(node):
    """Test if the given node is visible.

    This tests if the visibiliy attr is turned on for this node and all
    its parents.

    Args:
        node (str): node to test

    Returns:
        (bool): whether node is visible
    """
    _visible = cmds.getAttr(node+'.visibility')
    _parent = get_parent(node)
    if not _parent:
        return _visible
    return _visible and is_visible(_parent)


def load_plugin(plugin, verbose=0):
    """Wrapper for cmds.loadPlugin that doesn't error if plugin is loaded.

    Args:
        plugin (str): name of plugin to load
        verbose (int): print process data
    """
    if not cmds.pluginInfo(plugin, query=True, loaded=True):
        lprint('LOADING PLUGIN', plugin, verbose=verbose)
        cmds.loadPlugin(plugin)
    else:
        lprint('ALREADY LOADED:', plugin, verbose=verbose)


def multiply_node(input1, input2, output, force=False, name='multiply'):
    """Create a multiply node and use it to perform attr maths.

    Args:
        input1 (str): first input
        input2 (str|float): second input (or divide value)
        output (str): output node
        force (bool): force connect output (avoid already
            connected error)
        name (str): override attribute name

    Returns:
        (str): output attr
    """
    _out = divide_node(
        input1=input1, input2=input2, output=output, force=False,
        name=name)
    _out_node = _out.split('.')[0]
    cmds.setAttr(_out_node+'.operation', 1)
    return _out


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


def save_as(file_, revert_filename=True):
    """Save the current scene at the given path without changing cur filename.

    Args:
        file_ (str): path to save file to
        revert_filename (bool): disable revert filename
    """
    test_path(os.path.dirname(file_))
    _filename = cmds.file(query=True, location=True)
    cmds.file(rename=file_)
    cmds.file(save=True)
    if revert_filename:
        cmds.file(rename=_filename)


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


def set_val(attr, val, verbose=0):
    """Set value of the given attribute.

    This function aims to allow an attribute to be set without having to
    worry about its type, eg. string, float, col attrs.

    Args:
        attr (str): attribute to set
        val (any): value to apply
        verbose (int): print process data
    """
    _args = [val]
    _kwargs = {}
    if isinstance(val, qt.HColor):
        _args = val.to_tuple(mode='float')
    elif isinstance(val, six.string_types):
        _kwargs['type'] = 'string'
    elif isinstance(val, (list, tuple)):
        _args = val

    lprint('APPLYING VAL', attr, _args, _kwargs, verbose=verbose)
    cmds.setAttr(attr, *_args, **_kwargs)


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
