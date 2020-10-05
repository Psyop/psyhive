"""Represents an output referenced into a scene."""

from psyhive import tk2
from psyhive.utils import get_single, lprint

from maya_psyhive import ref


class OutputRef(ref.FileRef):
    """Represents a output file referenced into a scene."""

    def __init__(self, ref_node):
        """Constructor.

        Args:
            ref_node (str): reference node
        """
        super(OutputRef, self).__init__(ref_node)
        self.output = tk2.TTOutputFile(self.path)

    def _get_latest_path(self):
        """Get path to latest version of this output.

        Returns:
            (str): path to latest
        """
        try:
            _cur_asset = tk2.TTOutputFile(self.path)
        except ValueError:  # For cameras
            _cur_out = tk2.TTOutput(self.path)
            _latest_out = _cur_out.find_latest()
            if _latest_out == _cur_out:
                return self.path
            return get_single(_latest_out.find(type_='f'))
        return _cur_asset.find_latest().path

    def update_to_latest(self):
        """Update this output to latest version.

        Returns:
            (bool): whether update was required
        """
        _latest = self._get_latest_path()
        if self.path == _latest:
            return False
        lprint(' - UPDATING {} v{:03d} -> v{:03d}'.format(
            self.namespace, tk2.TTOutput(self.path).version,
            tk2.TTOutput(_latest).version))
        self.swap_to(_latest)
        return True
