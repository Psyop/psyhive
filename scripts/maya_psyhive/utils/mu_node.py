"""General node utilies."""

from maya import cmds

import six


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
        input1=input1, input2=input2, output=output, force=force,
        name=name)
    _out_node = _out.split('.')[0]
    cmds.setAttr(_out_node+'.operation', 1)
    return _out
