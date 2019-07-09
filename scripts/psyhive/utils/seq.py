"""Tools for managing sequences of files."""

import os

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.path import File, abs_path, find
from psyhive.utils.misc import system


class Seq(object):
    """Represents a sequences of files."""

    def __init__(self, path, frames=None):
        """Constructor.

        Args:
            path (str): path to file sequence (eg. "seq.%04d.jpg")
            frames (int list): force list of frames
        """
        self.path = abs_path(path)
        _file = File(self.path)
        self.dir = _file.dir
        self.extn = _file.extn
        assert '%04d' in self.path
        self.frame_expr = '%04d'
        if frames:
            self.set_frames(frames)

    def contains(self, file_):
        """Test if the given file is contained in this seq.

        ie. it matches the format string.

        Args:
            file_ (str): path to test

        Returns:
            (bool): whether file is member of this seq
        """
        _file = abs_path(file_)
        _head, _tail = self.path.split(self.frame_expr)
        if not (
                _file.startswith(_head) and
                _file.endswith(_tail)):
            return False
        _frame_str = _file[len(_head): -len(_tail)]
        if not _frame_str.isdigit():
            return False
        _frame = int(_frame_str)
        if self.frame_expr % _frame != _frame_str:
            return False
        return True

    def delete(self, wording='Remove', force=False):
        """Delete this sequence's frames.

        The user is asked to confirm before deletion.

        Args:
            wording (str): wording for confirmation dialog
            force (bool): force delete with no confirmation
        """
        from psyhive import qt
        from psyhive.utils import ints_to_str, get_plural

        _frames = self.get_frames(force=True)
        if not _frames:
            return
        if not force:
            qt.ok_cancel(
                '{} existing frame{} {} of seq?\n\n{}'.format(
                    wording, get_plural(_frames), ints_to_str(_frames),
                    self.path))
        for _path in self.get_paths():
            os.remove(_path)
        self.get_frames(force=True)

    @store_result_on_obj
    def get_frames(self, frames=None, force=False):
        """Get a list of frame indices from disk.

        Args:
            frames (int list): force frames (ie. don't read from disk)
            force (bool): force reread list from disk
        """
        if frames:
            return frames
        _frames = set()
        _head, _tail = self.path.split(self.frame_expr)
        for _file in find(self.dir, depth=1, extn=self.extn):
            if (
                    not _file.startswith(_head) or
                    not _file.endswith(_tail)):
                continue
            _frame_str = _file[len(_head): -len(_tail)]
            if not _frame_str.isdigit():
                continue
            _frame = int(_frame_str)
            _frames.add(_frame)

        return sorted(_frames)

    def get_path(self, idx):
        """Get the path to a frame of the sequence.

        Args:
            idx (int): frame number
        """
        return self.path % idx

    def get_paths(self):
        """Get a list of paths to the frames of this seq.

        Returns:
            (str list): list of paths
        """
        return [self[_frame] for _frame in self.get_frames()]

    def set_frames(self, frames):
        """Set cached list of frames.

        Args:
            frames (int list): list of frames to store
        """
        self.get_frames(force=True, frames=frames)

    def view(self):
        """View this image sequence."""
        _path = self.path.replace("%04d", "#")
        system('djv_view {}'.format(_path), verbose=1, result=False)

    def __getitem__(self, idx):
        return self.get_path(idx)

    def __repr__(self):
        return '<{}|{}>'.format(type(self).__name__.strip('_'), self.path)


class Collection(object):
    """Represents a collection of files."""

    def __init__(self, paths):
        """Constructor.

        Args:
            paths (str list): list of paths in collection
        """
        self._paths = paths

    def get_path(self, idx):
        """Get path for the given frame of this collection.

        Args:
            idx (int): frame index

        Returns:
            (str): path to frame
        """
        return self.get_paths()[idx]

    def get_paths(self):
        """Get a list of file paths in this collection."""
        return self._paths

    def __getitem__(self, idx):
        return self.get_path(idx)

    def __len__(self):
        return len(self.get_paths())
