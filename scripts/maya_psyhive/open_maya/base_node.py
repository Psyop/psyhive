"""Tools for managing the base node class."""

import os
import shutil
import tempfile

from maya import cmds, mel

import six

from psyhive.utils import (
    abs_path, diff, store_result, test_path, lprint, apply_filter)
from maya_psyhive.utils import create_attr, get_unique, add_to_set
from maya_psyhive.open_maya.plug import HPlug


class BaseNode(object):
    """Base class for any node object.

    All node classes should inherit from this one.
    """

    def __init__(self, node):
        """Constructor.

        Args:
            node (str): node name
        """
        if not isinstance(node, six.string_types):
            raise ValueError('Non-string init {} ({})'.format(
                node, type(node).__name__))
        self.node = node

    def compare(self, other):
        """Compare two nodes' settings.

        Args:
            other (BaseNode): node to compare with
        """
        _file_a, _file_b = [
            _node.save_preset('{}/{}.preset'.format(
                tempfile.gettempdir(),
                str(_node).replace(':', '_')))
            for _node in [self, other]]
        diff(_file_a, _file_b, check_extn=False)

    def create_attr(self, name, *args, **kwargs):
        """Add an attribute to this node.

        Args:
            name (str): attribute name

        Returns:
            (HPlug): new attribute plug
        """
        return HPlug(create_attr(self.node+'.'+name, *args, **kwargs))

    def add_to_set(self, set_):
        """Add this node to a set, creating it if required.

        Args:
            set_ (str): set to add to
        """
        add_to_set(self, set_)

    def delete(self):
        """Delete this object."""
        cmds.delete(self)

    def duplicate(self, name=None, **kwargs):
        """Duplicate this node.

        Args:
            name (str): name for duplicate

        Returns:
            (BaseNode): new node
        """
        _name = get_unique(name or self.node)
        _node = cmds.duplicate(self, name=_name, **kwargs)[0]
        return self.__class__(_node)

    def find_downstream(self, depth=1, type_=None, filter_=None, verbose=0):
        """Find nodes downstream from this one.

        Args:
            depth (int): max
            type_ (str): apply type filter
            filter_ (str): apply node name filter
            verbose (int): print process data

        Returns:
            (HFnDependencyNode list): downstream nodes
        """
        from maya_psyhive import open_maya as hom

        # Find connections
        _conns = set()
        _this_conns = set(self.list_connections(
            source=False, shapes=True) or [])
        for _conn in _this_conns:
            _conn = hom.HFnDependencyNode(_conn)
            _conns.add(_conn)
            lprint(' '*(5-depth), 'ADDING', _conn, verbose=0)
            if depth > 0:
                _conns |= set(_conn.find_downstream(
                    depth=depth-1, verbose=verbose))
        _conns = sorted(_conns)

        # Apply filters
        if type_:
            _conns = [
                _conn for _conn in _conns
                if _conn.object_type() == type_]
        if filter_:
            _conns = apply_filter(_conns, filter_, key=str)

        return _conns

    def _get_tmp_preset_path(self, use_mel):
        """Get path to tmp preset file.

        Args:
            use_mel (bool): use mel to load/save preset

        Returns:
            (str): path to tmp preset
        """
        _type = self.object_type()

        # Get presets dir
        _presets_dir = cmds.internalVar(userPresetsDir=True)
        assert _presets_dir.count(os.environ['USER']) == 1
        _presets_dir = abs_path('{}{}'.format(
            os.environ['HOME'], _presets_dir.split(os.environ['USER'])[-1]))

        # Get preset format
        if use_mel:
            _fmt = "{}/attrPresets/{}/tmp.mel"
        else:
            _fmt = "{}/{}Preset_tmp.mel"

        return _fmt.format(_presets_dir, _type)

    def has_attr(self, attr):
        """Check if the given attribute exists on this node.

        Args:
            attr (str): attribute name to test

        Returns:
            (bool): whether attr exists
        """
        return cmds.attributeQuery(attr, node=self, exists=True)

    def list_connections(self, **kwargs):
        """Wrapper for cmds.listConnections command.

        Returns:
            (list): connections
        """
        return cmds.listConnections(self, **kwargs)

    def list_relatives(self, **kwargs):
        """Wrapper for cmds.listRelatives command.

        Returns:
            (list): relatives
        """
        return cmds.listRelatives(self, **kwargs)

    def load_preset(self, file_, use_mel=True):
        """Load the given preset.

        Args:
            file_ (str): preset file to load
            use_mel (bool): preset was written using mel
        """
        _tmp_path = self._get_tmp_preset_path(use_mel=use_mel)
        test_path(os.path.dirname(_tmp_path))
        shutil.copy(file_, _tmp_path)
        if use_mel:
            _cmd = '{} "{}" "" "" "tmp" 1'.format(
                _get_load_preset_mel(), self)
            mel.eval(_cmd)
        else:
            cmds.nodePreset(load=(self, "tmp"))
        os.remove(_tmp_path)

    def object_type(self):
        """Wrapper for cmds.objectType command.

        Returns:
            (str): type name
        """
        return cmds.objectType(self)

    def plug(self, attr):
        """Get an attribute plug on this node.

        Args:
            attr (str): attribute name

        Returns:
            (HPlug): plug for attribute
        """
        if not isinstance(attr, six.string_types):
            raise ValueError('Non-string attr {} ({})'.format(
                attr, type(attr).__name__))
        return HPlug(self.plugs(attr))

    def plugs(self, attr):
        """Get an attribute on this node as a string.

        Args:
            attr (str): attribute name

        Returns:
            (str): full attribute name with node
        """
        return self.node+'.'+attr

    def save_preset(self, file_=None, use_mel=True, verbose=0):
        """Save preset for this node.

        Args:
            file_ (str): path to save preset at
            use_mel (bool): use mel to save preset
            verbose (int): print process data

        Returns:
            (str): preset path
        """
        _file = self._get_tmp_preset_path(use_mel=use_mel)
        if os.path.exists(_file):
            os.remove(_file)
        if use_mel:
            mel.eval('saveAttrPreset "{}" "tmp" false'.format(self))
        else:
            cmds.nodePreset(save=(self, "tmp"))
        lprint("SAVED PRESET", _file, verbose=verbose)
        assert os.path.exists(_file)

        if not file_:
            lprint("RETURNING ORIGINAL FILE", verbose=verbose)
            return _file

        shutil.move(_file, file_)
        return file_

    def select(self, **kwargs):
        """Wrapper for cmds.select as applied to this node."""
        cmds.select(self, **kwargs)

    def __add__(self, other):
        return str(self)+other

    def __cmp__(self, other):
        return cmp(str(self), str(other))

    def __hash__(self):
        return hash(str(self))

    def __str__(self):
        return self.node

    def __repr__(self):
        return '<{}:"{}">'.format(type(self).__name__, self.node)


@store_result
def _get_load_preset_mel():
    """Get apply preset mel and make sure files are sourced.

    Returns:
        (str): load preset mel
    """
    mel.eval('source presetMenuForDir')
    mel.eval('source updateAE')
    return 'applyPresetToNode'
