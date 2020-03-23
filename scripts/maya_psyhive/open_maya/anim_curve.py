"""Tools for managing anim curves."""

from maya import cmds
from maya.api import OpenMaya as om
from maya.api import OpenMayaAnim as oma

from psyhive.utils import get_single
from maya_psyhive.open_maya.base_node import BaseNode


class HFnAnimCurve(BaseNode, oma.MFnAnimCurve):
    """Wrapper for MFnAnimCurve object."""

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): anim curve node
        """
        super(HFnAnimCurve, self).__init__(node)
        _tmp_list = om.MSelectionList()
        _tmp_list.add(node)
        _obj = _tmp_list.getDependNode(0)
        oma.MFnAnimCurve.__init__(self, _obj)

    def connect(self, plug, force=False):
        """Connect this anim curve to the given plug.

        Args:
            plug (HPlug): plug to connect to
            force (bool): replace any existing connection
        """
        self.output.connect(plug, force=force)

    def get_key_frames(self):
        """Get a list of frames that are keyed in this curve.

        Returns:
            (float list): list of keyed frames
        """
        _ktvs = cmds.getAttr(self.plugs('keyTimeValue[:]'))
        return sorted(set([_frame for _frame, _ in _ktvs]))

    def get_key_range(self):
        """Get start/end of keyed range.

        Returns:
            (float tuple): start/end
        """
        _frames = self.get_key_frames()
        return min(_frames), max(_frames)

    def get_plug(self):
        """Get plug which this curve is driving.

        Returns:
            (HPlug): plug being driven
        """
        from maya_psyhive import open_maya as hom
        return hom.HPlug(self.get_plugs())

    def get_plugs(self):
        """Get name of plug which this curve is driving.

        Returns:
            (str): plug being driven
        """
        return get_single(
            self.output.list_connections(source=False, plugs=True))

    def is_static(self):
        """Test whether this is a static anim.

        Returns:
            (bool): whether anim is static
        """
        _ktv = get_single(cmds.getAttr(self.plug('keyTimeValue')))
        return bool(_ktv)

    def loop(self, plug=None, offset=False):
        """Loop this animation.

        Args:
            plug (HPlug): plug being driven (for efficiency)
            offset (bool): cycle with offset
        """
        _plug = plug or self.get_plug()
        _mode = 'cycle' if not offset else 'cycleRelative'
        cmds.setInfinity(_plug, preInfinite=_mode, postInfinite=_mode)

    @property
    def output(self):
        """Get output plug for this curve.

        Returns:
            (HPlug): output
        """
        return self.plug('output')

    def set_tangents(self, type_):
        """Set all tangents on this curve.

        Args:
            type_ (str): tangent type
        """
        cmds.keyTangent(self, inTangentType=type_, outTangentType=type_)
