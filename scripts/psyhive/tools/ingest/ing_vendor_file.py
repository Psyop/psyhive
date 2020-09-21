"""Tools for managing vendor delivery files.

The naming convention is:

    <tag>_<step>_<version>.<extn>

Where tag is a shot or asset name.
"""

from psyhive.utils import File

from . import ing_utils


class VendorFile(File):
    """Represents a correctly named outsource vendor file."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to file
        """
        super(VendorFile, self).__init__(file_)
        self.tag, self.step, self.version = ing_utils.parse_basename(
            self.basename)


def is_vendor_file(file_):
    """Test whether the given path is a correctly named vendor file.

    Args:
        file_ (str): path to test

    Returns:
        (bool): whether file is correctly named
    """
    try:
        VendorFile(file_)
    except ValueError:
        return False
    return True
