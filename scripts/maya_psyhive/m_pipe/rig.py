"""Tools for managing rigs."""

from psyhive.utils import store_result

from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_parent


class RigRef(ref.FileRef):
    """Represents a rig referenced into a scene."""

    @store_result
    def find_ctrls(self):
        """Find rig controls.

        Returns:
            (HFnTransform list): list of controls
        """
        _ctrls = set()
        for _ctrl_shp in self.find_nodes(type_='nurbsCurve'):
            _ctrl = hom.HFnTransform(get_parent(_ctrl_shp))
            _ctrls.add(_ctrl)
        return sorted(_ctrls)

    @store_result
    def find_plugs(self):
        """Find animatable rig plugs.

        Returns:
            (HPlug list): list of plugs
        """
        _plugs = []
        for _ctrl in self.find_ctrls():
            for _plug in _ctrl.find_plugs(keyable=True):
                _plugs.append(_plug)
        return _plugs


def get_selected_rig(catch=False):
    """Get selected rig.

    Args:
        catch (bool): no error on nothing selected

    Returns:
        (RigRef): selected rig
    """
    return ref.get_selected(class_=RigRef, catch=catch)
