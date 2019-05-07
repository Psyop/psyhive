"""Tools for managing references in maya."""

import os

from maya import cmds

from psyhive.utils import File, get_single, lprint


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

    def get_attr(self, attr):
        """Get an attribute on this rig.

        Args:
            attr (str): attribute name
        """
        return '{}:{}'.format(self.namespace, attr)

    def get_node(self, name):
        """Get node from this ref matching the given name.

        Args:
            name (str): name of node

        Returns:
            (str): node name
        """
        return '{}:{}'.format(self.namespace, name)

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

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.namespace)


def create_ref(file_, namespace):
    """Create a reference.

    Args:
        file_ (str): path to reference
        namespace (str): reference namespace

    Returns:
        (FileRef): reference
    """
    _file = File(file_)

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

    return FileRef(_ref)


def find_ref(namespace=None, catch=False):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match
        catch (bool): no error on fail to find matching ref

    Returns:
        (FileRef): matching ref
    """
    _refs = find_refs(namespace=namespace)
    return get_single(_refs, catch=catch)


def find_refs(namespace=None):
    """Find reference with given namespace.

    Args:
        namespace (str): namespace to match

    Returns:
        (FileRef list): scene refs
    """
    _refs = _read_refs()
    if namespace:
        _refs = [_ref for _ref in _refs if _ref.namespace == namespace]
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


def obtain_ref(file_, namespace):
    """Search for a reference and create it if it doesn't exist.

    Args:
        file_ (str): file to reference
        namespace (str): reference namespace
    """
    _ref = find_ref(namespace, catch=True)
    if _ref:
        assert _ref.file == file_
        return _ref

    return create_ref(file_=file_, namespace=namespace)


def _read_refs():
    """Read references in the scene."""
    return [FileRef(_ref) for _ref in cmds.ls(type='reference')]
