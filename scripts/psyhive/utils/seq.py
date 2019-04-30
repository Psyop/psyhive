"""Tools for managing sequences of files."""

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.path import File, abs_path


class Seq(object):
    """Represents a sequences of files."""

    def __init__(self, path, frames=None):
        """Constructor.

        Args:
            path (str): path to file sequence (eg. "seq.%04d.jpg")
            frames (int list): force list of frames
        """
        self.path = abs_path(path)
        self.dir = File(self.path).dir
        assert '%' in self.path
        if frames:
            self.set_frames(frames)

    def get_frame(self, idx):
        """Get the path to a frame of the sequence.

        Args:
            idx (int): frame number
        """
        return self.path % idx

    @store_result_on_obj
    def get_frames(self, frames=None, force=False):
        """Get a list of frame indices from disk.

        Args:
            frames (int list): force frames (ie. don't read from disk)
            force (bool): force reread list from disk
        """
        if frames:
            return frames
        print self.path
        raise NotImplementedError

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

    def __getitem__(self, idx):
        return self.get_frame(idx)

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

    def get_paths(self):
        """Get a list of file paths in this collection."""
        return self._paths
