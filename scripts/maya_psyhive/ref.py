"""Tools for managing references in maya."""

import operator
import os

from maya import cmds

from psyhive import qt
from psyhive.utils import File, get_single, lprint, apply_filter


class FileRef(object):
    """Represents a file referenced into maya."""

    def __init__(self, ref_node):
        """Constructor.

        Args:
            ref_node (str): reference node
        """
        self.ref_node = ref_node

    @property
    def _file(self):
        """Get this ref's file path (with copy number)."""
        try:
            return str(cmds.referenceQuery(self.ref_node, filename=True))
        except RuntimeError:
            return None

    def find_top_node(self):
        """Find top node of this reference.

        Returns:
            (HFnTransform): top node
        """
        _nodes = cmds.ls(
            self.namespace+":*", long=True, dagObjects=True,
            type='transform')
        _min_pipes = min([_node.count('|') for _node in _nodes])
        print 'MIN PIPES', _min_pipes
        _top_nodes = sorted(set([
            _node for _node in _nodes if _node.count('|') == _min_pipes]))
        print _top_nodes
        return get_single(_top_nodes).split('|')[-1]

    def get_attr(self, attr):
        """Get an attribute on this rig.

        Args:
            attr (str): attribute name
        """
        return '{}:{}'.format(self.namespace, attr)

    def get_node(self, name, class_=None):
        """Get node from this ref matching the given name.

        Args:
            name (str): name of node
            class_ (class): override node class

        Returns:
            (HFnDependencyNode): node name
        """
        from maya_psyhive import open_maya as hom
        _class = class_ or hom.HFnDependencyNode
        return _class('{}:{}'.format(self.namespace, name))

    def is_loaded(self):
        """Check if this reference is loaded.

        Returns:
            (bool): loaded state
        """
        return cmds.referenceQuery(self.ref_node, isLoaded=True)

    def load(self):
        """Load this reference."""
        cmds.file(self._file, loadReference=True)

    @property
    def namespace(self):
        """Get this ref's namespace."""
        return str(cmds.file(self._file, query=True, namespace=True))

    @property
    def path(self):
        """Get path to this ref's scene file (without copy number)."""
        if not self._file:
            return None
        return self._file.split('{')[0]

    def remove(self, force=False):
        """Remove this reference from the scene.

        Args:
            force (bool): remove without confirmation
        """
        if not force:
            _msg = (
                'Are you sure you want to remove the reference {}?\n\n'
                'This is not undoable.'.format(self.namespace))
            if not qt.yes_no_cancel(_msg) == 'Yes':
                return
        cmds.file(self._file, removeReference=True)

    def swap_to(self, file_):
        """Swap this reference file path.

        Args:
            file_ (str): new file path
        """
        if not os.path.exists(file_):
            raise OSError("Missing file: {}".format(file_))
        cmds.file(
            file_, loadReference=self.ref_node, ignoreVersion=True,
            options="v=0", force=True)

    def __cmp__(self, other):
        return cmp(self.ref_node, other.ref_node)

    def __hash__(self):
        return hash(self.ref_node)

    def __repr__(self):
        return '<{}:{}>'.format(
            type(self).__name__.strip('_'), self.namespace)


def create_ref(file_, namespace, class_=None):
    """Create a reference.

    Args:
        file_ (str): path to reference
        namespace (str): reference namespace
        class_ (type): override FileRef class

    Returns:
        (FileRef): reference
    """
    _file = File(file_)
    _class = class_ or FileRef

    # Test for existing
    cmds.namespace(set=":")
    if cmds.namespace(exists=namespace):
        raise NotImplementedError

    # Create the reference
    _cur_refs = set(cmds.ls(type='reference'))
    _kwargs = {
        'reference': True,
        'namespace': namespace,
        'options': "v=0;p=17",
        'ignoreVersion': True}
    cmds.file(_file.abs_path(), **_kwargs)

    # Find new reference node
    _ref = get_single(set(cmds.ls(type='reference')).difference(_cur_refs))

    return _class(_ref)


def find_ref(
        namespace=None, filter_=None, catch=False, class_=None, verbose=0):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match
        filter_ (str): apply filter to names list
        catch (bool): no error on fail to find matching ref
        class_ (FileRef): override FileRef class
        verbose (int): print process data

    Returns:
        (FileRef): matching ref
    """
    _refs = find_refs(namespace=namespace, filter_=filter_, class_=class_)
    lprint('Found {:d} refs'.format(len(_refs)), _refs, verbose=verbose)
    return get_single(_refs, catch=catch)


def find_refs(namespace=None, filter_=None, class_=None):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match
        filter_ (str): namespace filter
        class_ (FileRef): override FileRef class

    Returns:
        (FileRef list): scene refs
    """
    _refs = _read_refs(class_=class_)
    if namespace:
        _refs = [_ref for _ref in _refs if _ref.namespace == namespace]
    if filter_:
        _refs = apply_filter(
            _refs, filter_, key=operator.attrgetter('namespace'))
    return _refs


def get_selected(catch=False, multi=False, verbose=0):
    """Get selected ref.

    Args:
        catch (bool): no error on None
        multi (bool): allow multiple selections
        verbose (int): print process data

    Returns:
        (FileRef): selected file ref
        (None): if no ref is selected and catch used

    Raises:
        (ValueError): if no ref is selected
    """
    _nss = sorted(set([
        _node.split(":")[0] for _node in cmds.ls(selection=True)
        if ":" in _node]))
    lprint('SEL NAMESPACES', _nss, verbose=verbose)
    _refs = [find_ref(_ns) for _ns in _nss]
    _sel_ref_nodes = [
        FileRef(_ref_node) for _ref_node in cmds.ls(
            selection=True, type='reference')]
    lprint('SEL REF NODES', _sel_ref_nodes, verbose=verbose)
    _refs += _sel_ref_nodes
    lprint('REFS', _refs, verbose=verbose)
    if multi:
        return _refs
    _ref = get_single(
        _refs, fail_message='No reference selected', catch=catch)
    if not _ref:
        return None
    return _ref


def obtain_ref(file_, namespace, class_=None):
    """Search for a reference and create it if it doesn't exist.

    Args:
        file_ (str): file to reference
        namespace (str): reference namespace
        class_ (FileRef): override FileRef class
    """
    _ref = find_ref(namespace, catch=True, class_=class_)
    if _ref:
        assert _ref.path == file_
        return _ref

    return create_ref(file_=file_, namespace=namespace, class_=class_)


def _read_refs(class_=None):
    """Read references in the scene.

    Args:
        class_ (FileRef): override FileRef class - any refs which raise
            a ValueError on init are excluded from the list

    Returns:
        (FileRef list): list of refs
    """
    _class = class_ or FileRef
    _refs = []
    for _ref_node in cmds.ls(type='reference'):
        try:
            _ref = _class(_ref_node)
        except ValueError:
            continue
        _refs.append(_ref)
    return _refs
