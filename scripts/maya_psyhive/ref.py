"""Tools for managing references in maya."""

from maya import cmds

from psyhive.utils import File, get_single


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
        return cmds.referenceQuery(self.ref_node, filename=True)

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

    @property
    def namespace(self):
        """Get this ref's namespace."""
        return cmds.file(self._file, query=True, namespace=True)

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
    """
    _refs = _read_refs()
    if namespace:
        _refs = [_ref for _ref in _refs if _ref.namespace == namespace]
    return get_single(_refs, catch=catch)


def get_selected(catch=False):
    """Get selected ref.

    Args:
        catch (bool): no error on None

    Returns:
        (FileRef): selected file ref
        (None): if no ref is selected and catch used

    Raises:
        (ValueError): if no ref is selected
    """
    _nss = sorted(set([
        _node.split(":")[0] for _node in cmds.ls(selection=True)
        if ":" in _node]))
    _ns = get_single(
        _nss, fail_message='No reference selected', catch=catch)
    if not _ns:
        return None
    return find_ref(_ns)


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
