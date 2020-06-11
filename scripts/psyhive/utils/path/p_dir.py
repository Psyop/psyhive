"""Tools for managing the directory object."""

import os
import shutil

from ..misc import system

from .p_path import Path
from .p_utils import restore_cwd


class Dir(Path):
    """Represents a directory on disk."""

    def delete(self, force=False, wording='delete'):
        """Delete this directory.

        Args:
            force (bool): force delete with no confirmation
            wording (str): override wording for dialog
        """
        if not self.exists():
            return
        if not force:
            from psyhive import qt
            qt.ok_cancel(
                "{} this directory?\n\n{}".format(
                    wording.capitalize(), self.path),
                title='Confirm '+wording)
        shutil.rmtree(self.path)

    def find(self, **kwargs):
        """Search for files in this dir.

        Returns:
            (str list): list of files
        """
        from .p_tools import find
        return find(self.path, **kwargs)

    @restore_cwd
    def launch_browser(self):
        """Launch browser set to this dir."""
        print 'LAUNCH BROWSER'
        os.chdir(self.path)
        system('explorer .', verbose=1)

    def test_path(self):
        """Test this dir exists, creating if needed."""
        from .p_tools import test_path
        test_path(self.path)
