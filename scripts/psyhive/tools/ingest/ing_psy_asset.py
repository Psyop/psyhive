"""Tools for psyop files.

These follow the naming convention:

    <asset>_

"""

from psyhive.utils import File
from . import ing_utils


class PsyAsset(File):
    """Represents a psyop asset file.

    This is used to recognise references to psyop assets in vendor files.
    """

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to file
        """
        super(PsyAsset, self).__init__(file_)
        _data = ing_utils.parse_seq_basename(self.basename)
        self.asset, self.step, self.output_type, self.version, _null = _data
        assert not _null


def is_psy_asset(file_):
    """Test whether the given path is a correctly named psyop asset.

    Args:
        file_ (str): path to test

    Returns:
        (bool): whether file is correctly named
    """
    try:
        PsyAsset(file_)
    except ValueError:
        return False
    return True
