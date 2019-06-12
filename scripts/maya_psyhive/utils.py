"""General utilties for maya."""

import functools

from maya import cmds
import six

from psyhive.utils import get_single


COLS = (
    "deepblue", "black", "darkgrey", "grey", "darkred", "darkblue", "blue",
    "darkgreen", "deepgrey", "magenta", "brown", "deepbrown", "redbrown",
    "red", "green", "fadedblue", "white", "yellow", "lightblue", "lightgreen",
    "pink", "orange", "lightyellow", "fadedgreen", "darktan", "tanyellow",
    "olivegreen", "woodgreen", "cyan", "greyblue", "purple", "crimson")


def restore_ns(func):
    """Decorator to execute a function, restoring the original namespace.

    Args:
        func (fn): function to decorate

    Returns:
        (fn): decorated function
    """

    def _restore_ns_fn(*args, **kwargs):
        _ns = ':'+cmds.namespaceInfo(currentNamespace=True)
        _result = func(*args, **kwargs)
        cmds.namespace(set=_ns)
        return _result

    return _restore_ns_fn


def add_attr(attr, value, keyable=True, update=True):
    """Add an attribute.

    Args:
        attr (str): attr name (eg. persp1.blah)
        value (any): attribute value to apply
        keyable (bool): keyable state of attribute

    Returns:
        (str): full attribute name (eg. persp.blah)
    """
    _node, _attr = attr.split('.')

    # Create attr
    _type = None
    _created = False
    if not cmds.attributeQuery(_attr, node=_node, exists=True):
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
        cmds.addAttr(_node, **_kwargs)
        _created = True

    # Set attr
    if not get_attr(attr) == value and (_created or update):
        _kwargs = {}
        if isinstance(value, six.string_types):
            _kwargs['type'] = 'string'
        cmds.setAttr(attr, value, **_kwargs)

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


@restore_ns
def add_to_set(obj, set_):
    """Add the given object to the given set, creating it if required.

    Args:
        obj (str): object to add
        set_ (str): name of set to add to
    """
    if not cmds.objExists(set_):
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


def divide_node(input1, input2, output, force=False, name='divide'):
    """Create a divide node and use it to perform attr maths.

    Args:
        input1 (str): first input
        input2 (str|float): second input (or divide value)
        output (str): output node
        force (bool): force connect output (avoid already
            connected error)

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



def get_attr(attr):
    """Read an attribute value.

    This handles different attribute types without requiring extra flags.
    For example, a string attr will be read as a string.

    Args:
        attr (str): attr to read

    Returns:
        (any): attribute value
    """
    _node, _attr = attr.split('.')
    _type = cmds.attributeQuery(_attr, node=_node, attributeType=True)

    _kwargs = {}
    if _type == 'typed':
        _kwargs['asString'] = True
    elif _type in ['float', 'long', 'doubleLinear']:
        pass
    else:
        raise ValueError(_type)

    return cmds.getAttr(attr, **_kwargs)


def get_shp(node):
    """Get the shape of the given node.

    Args:
        node (str): node to read

    Returns:
        (str): shape node
    """
    return get_single(cmds.listRelatives(node, shapes=True))


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


def multiply_node(input1, input2, output, force=False, name='multiply'):
    """Create a multiply node and use it to perform attr maths.

    Args:
        input1 (str): first input
        input2 (str|float): second input (or divide value)
        output (str): output node
        force (bool): force connect output (avoid already
            connected error)

    Returns:
        (str): output attr
    """
    _out = divide_node(
        input1=input1, input2=input2, output=output, force=False,
        name=name)
    _out_node = _out.split('.')[0]
    # print 'OUT NODE', _out_node, cmds.objExists(_out_node), type(_out_node)
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
