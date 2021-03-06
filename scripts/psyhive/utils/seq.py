"""Tools for managing sequences of files."""

import collections
import operator
import os
import shutil
import time

from .cache import store_result_on_obj
from .misc import dprint, lprint, get_plural, bytes_to_str
from .filter_ import passes_filter
from .path import (
    File, abs_path, find, test_path, Dir, nice_size, get_path, Path)
from .range_ import ints_to_str


class Seq(object):
    """Represents a sequences of files."""

    def __init__(self, path, frames=None, safe=True):
        """Constructor.

        Args:
            path (str): path to file sequence (eg. "seq.%04d.jpg")
            frames (int list): force list of frames
            safe (bool): enforce blah.%04d.extn naming
        """
        self.path = abs_path(path)
        _file = File(self.path)
        self.dir = _file.dir
        self.extn = _file.extn
        self.frame_expr = '%04d'
        self.filename = _file.filename
        if safe:
            if not _file.filename.count('.%04d.') == 1:
                raise ValueError(path)
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

    def copy_to(self, seq, parent=None):
        """Copy this sequence to a new location.

        Args:
            seq (Seq): target location
            parent (QDialog): parent dialog for progress bar
        """
        from psyhive import qt
        seq.delete(wording='Replace')
        seq.test_dir()
        for _frame in qt.progress_bar(
                self.get_frames(), 'Copying {:d} frame{}',
                parent=parent):
            shutil.copy(self[_frame], seq[_frame])

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

    def delete(self, wording='remove', force=False, frames=None, icon=None):
        """Delete this sequence's frames.

        The user is asked to confirm before deletion.

        Args:
            wording (str): wording for confirmation dialog
            force (bool): force delete with no confirmation
            frames (int list): list of frames to delete (if not all)
            icon (str): override interface icon
        """
        from psyhive import qt

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
                title='Confirm '+wording, icon=icon)
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

    def get_size(self):
        """Get size in bytes of this file sequence.

        Returns:
            (int): size in bytes
        """
        _size = 0
        for _path in self.get_paths():
            _size += File(_path).get_size()
        return _size

    def has_missing_frames(self):
        """Test if this sequence has missing frames.

        ie. every frame exists between the start and end frames.

        Returns:
            (bool): whether missing frames
        """
        _start, _end = self.find_range()
        return self.get_frames() != range(_start, _end+1)

    def move_to(self, target):
        """Move this image sequence.

        Args:
            target (Seq): where to move to
        """
        assert not target.exists(force=True)
        target.test_dir()
        for _frame in self.get_frames(force=True):
            shutil.move(self[_frame], target[_frame])

    def nice_size(self):
        """Get size of this image sequence in a readable form.

        Returns:
            (str): size string
        """
        return bytes_to_str(self.get_size())

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

    def to_mov(self, file_, convertor=None, fps=None, force=False, view=False):
        """Generate a mov from this image sequence.

        Args:
            file_ (str): path to mov file
            convertor (str): tool to use to generate mov
            fps (float): override mov frame rate (default is host fps)
            force (bool): overwwrite existing without confirmation
            view (bool): view mov on generation
        """
        from psyhive import host

        _mov = Movie(get_path(file_))
        _conv = convertor or os.environ.get('PSYHIVE_CONVERTOR', 'ffmpeg')
        _fps = fps or host.get_fps()

        _mov.delete(wording='replace', force=force)
        if _conv == 'moviepy':
            _seq_to_mov_moviepy(self, _mov.path, fps=_fps)
        elif _conv == 'ffmpeg':
            _seq_to_mov_ffmpeg(self, _mov.path, fps=_fps)
        else:
            raise ValueError(_conv)

        if view:
            _mov.view()

        return _mov

    def view(self, viewer=None, verbose=0):
        """View this image sequence.

        Args:
            viewer (str): viewer to use
            verbose (int): print process data
        """
        _view_seq(self.path, viewer=viewer, verbose=verbose)

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

    def view(self, viewer=None, verbose=0):
        """View this movie.

        Args:
            viewer (str): override movie viewer
            verbose (int): print process data
        """
        _view_seq(self.path, viewer=viewer, verbose=verbose)


def _view_seq(path, viewer=None, verbose=0):
    """View an image sequence or movie file.

    Args:
        path (str): path to images/movie to view
        viewer (str): viewer to use
        verbose (int): print process data
    """
    _viewer = viewer or os.environ.get('VIEWER', 'rv')
    print 'VIEW SEQ', path, _viewer

    if _viewer == 'djv_view':
        _path = path.replace("%04d", "#")
        _cmd = 'djv_view "{}" &'.format(_path)
        lprint(_cmd, verbose=verbose)
        os.system(_cmd)

    elif _viewer == 'rv':
        import psylaunch
        dprint('Launching psylaunch rv')
        psylaunch.launch_app('rv', args=[path, '-play'])

    else:
        raise ValueError(_viewer)


def _seq_to_mov_moviepy(seq, mov, fps, audio=None, audio_offset=0.0):
    """Genreate a to mov using moviepy.

    Args:
        seq (Seq): input sequence
        mov (str): output mov
        fps (float): mov frame rate
        audio (str): path to audio
        audio_offset (float): apply audio offset
    """
    import moviepy.editor as mpy

    _start = time.time()
    _frames = seq.get_frames()
    print 'FRAMES', ints_to_str(_frames)
    _mov = Movie(abs_path(mov))
    print 'OUT FILE', _mov
    print 'FPS', fps

    # Build moviepy object
    _clip = mpy.ImageSequenceClip(seq.dir, fps=fps)

    # Add audio
    if audio:
        _audio = mpy.AudioFileClip(audio)
        if audio_offset:
            _audio = _audio.subclip(audio_offset)
        _audio = _audio.set_duration(_clip.duration)
        _clip.audio = _audio

    # Write mov
    _mov.delete()
    _mov.test_dir()
    _clip.write_videofile(_mov, codec="libx264")
    dprint('WROTE VIDEO {} {:.02f}s {}'.format(
        nice_size(_mov), time.time()-_start, _mov))


def _seq_to_mov_ffmpeg(seq, mov, fps):
    """Generate a mov using ffmpeg.

    Args:
        seq (Seq): input sequence
        mov (str): output mov
        fps (float): mov frame rate
    """
    from psyhive import pipe

    _start, _end = seq.find_range(force=True)
    _mov = Movie(get_path(mov))
    assert not _mov.exists()
    assert _mov.extn.lower() in ['mov', 'mp4']
    _mov.test_dir()

    # Use ffmpeg through psylaunch
    if pipe.LOCATION == 'psy':
        import psylaunch
        _args = [
            '-r', str(fps),
            '-f', 'image2',
            '-i', seq.path,
            '-vcodec', 'libx264',
            '-crf', '25',
            '-pix_fmt', 'yuv420p',
            _mov.path]
        print 'launch ffmpeg --', ' '.join(_args)
        psylaunch.launch_app('ffmpeg', args=_args, wait=True)

    # Use ffmpeg directly
    else:
        _args = [
            'ffmpeg',
            '-r', str(fps),
            '-f', 'image2',
            '-i', '"{}"'.format(seq.path),
            '-vcodec', 'libx264',
            '-crf', '25',
            '-pix_fmt', 'yuv420p',
            '"{}"'.format(_mov.path)]
        if _start != 1:
            _idx = _args.index('-i')
            _args.insert(_idx, '-start_number')
            _args.insert(_idx+1, str(_start))
        _cmd = ' '.join(_args)
        print _cmd
        os.system(_cmd)

    if not _mov.exists():
        raise RuntimeError("Failed to generate "+_mov.path)


def find_seqs(dir_, class_=None, filter_=None, verbose=0):
    """Find sequences in the given path and subdirs.

    Args:
        dir_ (str): path to dir to search
        class_ (class): override seq class
        filter_ (str): apply path filter
        verbose (int): print process data

    Returns:
        (Seq list): list of seqs
    """
    _dir = Dir(abs_path(dir_))
    _class = class_ or Seq

    _this_seqs = collections.defaultdict(set)
    _seqs = []
    for _path in _dir.find(depth=1, class_=Path):

        lprint(' - TESTING FILE', _path, verbose=verbose > 2)

        if _path.is_file():

            if filter_ and not passes_filter(_path.path, filter_):
                continue

            # Ignore files already matched in seq
            _already_matched = False
            for _seq in _this_seqs:
                if _seq.contains(_path):
                    _already_matched = True
                    _frame = _seq.get_frame(_path)
                    _this_seqs[_seq].add(_frame)
                    lprint(' - EXISTING SEQ', _path, verbose=verbose > 2)
                    break
            if _already_matched:
                continue

            # Match seq
            _seq = seq_from_frame(_path, catch=True, class_=_class)
            if _seq:
                lprint(' - CREATED SEQ', _seq, verbose=verbose)
                _frame = _seq.get_frame(_path)
                _this_seqs[_seq].add(_frame)

        elif _path.is_dir():
            _seqs += find_seqs(
                _path, class_=class_, verbose=verbose, filter_=filter_)

        else:
            raise ValueError(_path)

    # Apply frames cache
    for _seq, _frames in _this_seqs.items():
        _seq.set_frames(sorted(_frames))

    return sorted(_seqs+_this_seqs.keys(), key=operator.attrgetter('path'))


def seq_from_frame(file_, catch=False, class_=None):
    """Get a sequence object from the given file path.

    Args:
        file_ (str): path to frame of a sequence
        catch (bool): no error on fail to find seq
        class_ (str): override seq class

    Returns:
        (Seq): file's sequence
    """
    _file = File(file_)
    _class = class_ or Seq

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
        return _class(_path)
    except ValueError:
        return None
