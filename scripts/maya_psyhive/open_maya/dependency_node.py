"""Tools for managing dependency nodes."""

from maya.api import OpenMaya as om

from maya_psyhive.open_maya.base_node import BaseNode


class HFnDependencyNode(BaseNode, om.MFnDependencyNode):
    """Wrapper for MFnDependencyNode object."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): dependency node name
        """
        super(HFnDependencyNode, self).__init__(node)
        _tmp_list = om.MSelectionList()
        try:
            _tmp_list.add(node)
        except RuntimeError as _exc:
            if _exc.message.endswith('Object does not exist'):
                raise RuntimeError('missing node - {}'.format(node))
            raise _exc
        _obj = _tmp_list.getDependNode(0)
        om.MFnDependencyNode.__init__(self, _obj)
