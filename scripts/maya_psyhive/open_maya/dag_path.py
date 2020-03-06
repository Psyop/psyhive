"""Tools for managing dag path nodes."""

from maya.api import OpenMaya as om

import six


class HDagPath(om.MDagPath):
    """Wrapper for MDagPath with simpler init."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): path to dag node
        """
        self.node = node
        if not isinstance(node, six.string_types):
            raise ValueError('Bad node {} ({})'.format(
                node, type(node).__name__))
        _tmp_list = om.MSelectionList()
        _tmp_list.add(node)
        self._obj = _tmp_list.getDependNode(0)
        super(HDagPath, self).__init__(_tmp_list.getDagPath(0))

    def inclusive_matrix(self):
        """Get world space matrix for this dag object.

        Returns:
            (HMatrix): matrix
        """
        from maya_psyhive import open_maya as hom
        return hom.HMatrix(self.inclusiveMatrix())

    def __repr__(self):
        return "<{}|{}>".format(type(self).__name__, self.partialPathName())
