"""Tools for managing the directory object."""

import os
import shutil

from ..misc import system

from .p_path import Path
from .p_utils import restore_cwd


class Dir(Path):
    """Represents a directory on disk."""

    def contains(self, path):
        """Test if the given path is within this directory.

        Args:
            path (str): path to test

        Returns:
            (bool): whether path in within this dir
        """
        from .p_tools import abs_path, get_path
        _path = get_path(path)
        return abs_path(_path).startswith(abs_path(self.path))

    def copy_to(self, trg, force=False):
        """Copy this dir to another location.

        Args:
            trg (str|Dir): target location
            force (bool): replace existing without confirmation
        """
        from .p_tools import get_path
        assert self.exists()
        assert self.is_dir()
        _target = Dir(get_path(trg))
        _target.delete(force=force)
        shutil.copytree(self.path, _target.path)

    def delete(self, force=False, wording='delete', icon=None):
        """Delete this directory.

        Args:
            force (bool): force delete with no confirmation
            wording (str): override wording for dialog
            icon (str): override interface icon
        """
        if not self.exists():
            return
        if not force:
            from psyhive import qt
            qt.ok_cancel(
                "{} this directory?\n\n{}".format(
                    wording.capitalize(), self.path),
                title='Confirm '+wording, icon=icon)
        shutil.rmtree(self.path)

    def find(self, **kwargs):
        """Search for files in this dir.

        Returns:
            (str list): list of files
        """
        from .p_tools import find
        return find(self.path, **kwargs)

    def find_seqs(self, **kwargs):
        """Find file sequences within this dir.

        Returns:
            (Seq list): sequences
        """
        from ..seq import find_seqs
        return find_seqs(self.path, **kwargs)

    def get_file(self, filename):
        """Get child file of this directory.

        Args:
            filename (str): name of file (eg. text.txt)

        Returns:
            (File): file object
        """
        from .p_file import File
        return File(self.path+'/'+filename)

    def get_subdir(self, dirname):
        """Get child dir of this directory.

        Args:
            dirname (str): name of dir

        Returns:
            (Dir): dir object
        """
        return Dir(self.path+'/'+dirname)

    @restore_cwd
    def launch_browser(self):
        """Launch browser set to this dir."""
        print 'LAUNCH BROWSER'
        os.chdir(self.path)
        system('explorer .', verbose=1)

    def move_to(self, trg, force=False):
        """Move this dir to another location.

        Args:
            trg (str|Dir): target location
            force (bool): replace existing without confirmation
        """
        from .p_tools import get_path
        assert self.exists()
        assert self.is_dir()
        _target = Dir(get_path(trg))
        _target.delete(force=force)
        shutil.move(self.path, _target.path)

    def test_path(self):
        """Test this dir exists, creating if needed."""
        from .p_tools import test_path
        test_path(self.path)
