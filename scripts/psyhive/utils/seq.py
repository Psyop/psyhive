"""Tools for managing sequences of files."""

import os

from psyhive.utils.cache import store_result_on_obj
from psyhive.utils.path import File, abs_path, find, test_path, Dir
from psyhive.utils.misc import system, dprint, lprint


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
        if not _file.filename.count('.%04d.') == 1:
            raise ValueError(path)
        self.frame_expr = '%04d'
        self.basename = _file.filename.split('.%04d.')[0]
        if frames:
            self.set_frames(frames)

    def add_frame(self, frame):
        """Add frame the given frame to the cached frames list.

        Args:
            frame (int): frame to add
        """
        _frames = set(self.get_frames())
        _frames.add(frame)
        self.set_frames(sorted(_frames))

    def contains(self, file_):
        """Test if the given file is contained in this seq.

        ie. it matches the format string.

        Args:
            file_ (str): path to test

        Returns:
            (bool): whether file is member of this seq
        """
        _frame = self.get_frame(file_)
        return _frame is not None

    def delete(self, wording='remove', force=False, frames=None):
        """Delete this sequence's frames.

        The user is asked to confirm before deletion.

        Args:
            wording (str): wording for confirmation dialog
            force (bool): force delete with no confirmation
            frames (int list): list of frames to delete (if not all)
        """
        from psyhive import qt
        from psyhive.utils import ints_to_str, get_plural

        _frames = self.get_frames(force=True)
        if frames:
            _frames = sorted(set(_frames).intersection(frames))
        if not _frames:
            return
        if not force:
            qt.ok_cancel(
                '{} existing frame{} {} of image sequence?\n\n{}'.format(
                    wording.capitalize(), get_plural(_frames),
                    ints_to_str(_frames), self.path),
                title='Confirm '+wording)
        for _frame in _frames:
            os.remove(self[_frame])
        self.get_frames(force=True)

    def exists(self, force=False, verbose=0):
        """Test if this image sequence exists.

        Args:
            force (bool): force reread frames from disk
            verbose (int): print process data

        Returns:
            (bool): whether sequence exists
        """
        return bool(self.get_frames(force=force, verbose=verbose))

    def find_range(self, force=False):
        """Find range of this sequence's frames.

        Args:
            force (bool): force reread range from disk

        Returns:
            (tuple): start/end frames
        """
        _frames = self.get_frames(force=force)
        if not _frames:
            return None
        return _frames[0], _frames[-1]

    def get_frame(self, file_):
        """Get frame number of the given member of this sequence.

        If the file isn't a frame of this sequence then the function
        returns None.

        Args:
            file_ (str): path to file

        Returns:
            (int|None): frame number (if any)
        """
        _file = abs_path(file_)
        _head, _tail = self.path.split(self.frame_expr)
        if not (
                _file.startswith(_head) and
                _file.endswith(_tail)):
            return None
        _frame_str = _file[len(_head): -len(_tail)]
        if not _frame_str.isdigit():
            return None
        _frame = int(_frame_str)
        if self.frame_expr % _frame != _frame_str:
            return None
        return _frame

    @store_result_on_obj
    def get_frames(self, frames=None, force=False, verbose=0):
        """Get a list of frame indices from disk.

        Args:
            frames (int list): force frames (ie. don't read from disk)
            force (bool): force reread list from disk
            verbose (int): print process data

        Returns:
            (int list): frame numbers
        """
        if frames:
            return frames
        _frames = set()
        _head, _tail = self.path.split(self.frame_expr)

        _files = find(self.dir, depth=1, extn=self.extn)
        if verbose:
            print 'CHECKING {:d} FILES IN DIR {}'.format(len(_files), self.dir)
            print ' - HEAD', _head
            print ' - TAIL', _tail

        for _file in _files:
            if not _file.startswith(_head):
                lprint(' - REJECTED HEAD', _file, verbose=verbose)
                continue
            if not _file.endswith(_tail):
                lprint(' - REJECTED TAIL', _file, verbose=verbose)
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

    def has_missing_frames(self):
        """Test if this sequence has missing frames.

        ie. every frame exists between the start and end frames.

        Returns:
            (bool): whether missing frames
        """
        _start, _end = self.find_range()
        return self.get_frames() != range(_start, _end+1)

    def parent(self):
        """Get parent dir of this seq.

        Returns:
            (Dir): parent
        """
        return Dir(self.dir)

    def set_frames(self, frames):
        """Set cached list of frames.

        Args:
            frames (int list): list of frames to store
        """
        self.get_frames(force=True, frames=frames)

    def test_dir(self):
        """Test this sequence's parent directory exists."""
        test_path(self.dir)

    def view(self, viewer=None):
        """View this image sequence.

        Args:
            viewer (str): viewer to use
        """
        _view_seq(self.path, viewer=viewer)

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


class Movie(File):
    """Represents a movie file, eg. a mov/mp4."""

    def view(self, viewer=None):
        """View this movie.

        Args:
            viewer (str): override movie viewer
        """
        _view_seq(self.path, viewer=viewer)


def _view_seq(path, viewer=None):
    """View an image sequence or movie file.

    Args:
        path (str): path to images/movie to view
        viewer (str): viewer to use
    """
    _viewer = viewer or os.environ.get('VIEWER', 'rv')
    print 'VIEW SEQ', path, _viewer

    if _viewer == 'djv_view':
        _path = path.replace("%04d", "#")
        system('djv_view {}'.format(_path), result=False, verbose=1)

    elif _viewer == 'rv':
        import psylaunch
        dprint('Launching psylaunch rv')
        psylaunch.launch_app('rv', args=[path, '-play'])

    else:
        raise ValueError(_viewer)


def seq_from_frame(file_, catch=False):
    """Get a sequence object from the given file path.

    Args:
        file_ (str): path to frame of a sequence
        catch (bool): no error on fail to find seq

    Returns:
        (Seq): file's sequence
    """
    _file = File(file_)
    _tokens = _file.basename.split('.')
    if not len(_tokens) >= 2:
        if catch:
            return None
        raise ValueError(file_)
    _frame = _tokens[-1]
    if not _frame.isdigit():
        if catch:
            return False
        raise ValueError(file_)
    _base = '.'.join(_tokens[:-1])
    _path = '{}/{}.%0{:d}d.{}'.format(
        _file.dir, _base, len(_frame), _file.extn)
    try:
        return Seq(_path)
    except ValueError:
        return None
