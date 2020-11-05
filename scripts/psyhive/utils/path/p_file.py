"""Tools for managing the file object."""

import filecmp
import os
import shutil
import tempfile

from ..misc import system, dprint

from .p_path import Path


class File(Path):
    """Represents a file on disk."""

    def apply_extn(self, extn):
        """Update this file path with a different extension.

        Args:
            extn (str): new extension

        Returns:
            (File): new file path
        """
        return File('{}/{}.{}'.format(self.dir, self.basename, extn))

    def copy_to(self, file_, diff_=False, force=False):
        """Copy this file to another location.

        Args:
            file_ (str): target path
            diff_ (bool): show diffs before copying files
            force (bool): overwrite existing without confirmation
        """
        from psyhive import qt
        from .p_tools import get_path, test_path

        _file = get_path(file_)
        test_path(os.path.dirname(_file))
        if os.path.exists(_file):

            if self.matches(_file):
                print 'MATCH'
                return
            print 'NO MATCH'

            if diff_:
                self.diff(_file)
                if self.matches(_file):
                    print 'POST DIFF: MATCH'
                    return

            if not force:
                _result = qt.yes_no_cancel("Replace existing file?\n\n"+_file)
                if _result == 'No':
                    return

        assert not self.path == _file
        shutil.copy(self.path, _file)

    def delete(self, force=False, wording='delete', catch=False):
        """Delete this file.

        Args:
            force (bool): delete with no confirmation
            wording (str): wording for confirmation dialog
            catch (bool): no error on fail to delete
        """
        if not self.exists():
            return
        if not force:
            from psyhive import qt
            qt.ok_cancel("{} file?\n\n{}".format(
                wording.capitalize(), self.path))

        try:
            os.remove(self.path)
        except OSError as _exc:
            print 'FAILED TO DELETE', self.path
            if not catch:
                return

    def diff(self, other, label=None, check_extn=True):
        """Show diffs between this and another text file.

        Args:
            other (str): path to other file
            label (str): pass label to diff app
            check_extn (bool): check extension is approved (to avoid
                binary compares)
       """
        from .p_tools import diff

        _other = other
        if isinstance(_other, File):
            _other = _other.path
        diff(self.path, _other, label=label, check_extn=check_extn)

    def edit(self, line_n=None, verbose=0):
        """Edit this file in a text editor.

        Args:
            line_n (int): line of the file to open
            verbose (int): print process data
        """
        from ..misc import lprint
        from .p_tools import abs_path

        _arg = self.path
        if line_n:
            _arg += ':{:d}'.format(line_n)

        # Try using sublime executable
        _subl_exe = os.environ.get('SUBLIME_EXE')
        if not _subl_exe:
            for _exe in [
                    'C:/Program Files/Sublime Text 3/subl.exe',
                    'C:/Program Files (x86)/Sublime Text 3/subl.exe',
            ]:
                if os.path.exists(_exe):
                    _subl_exe = abs_path(_exe, win=os.name == 'nt')
                    break
                lprint('MISSING EXE', _exe, verbose=verbose)
        if _subl_exe:
            lprint('EXE', _subl_exe, verbose=verbose)
            _cmds = [_subl_exe, _arg]
            system(_cmds, verbose=verbose, result=False)
            return

        # Try using psylaunch
        dprint('Using psylaunch sublime - it may be quicker to install it '
               'locally on your machine.')
        import psylaunch
        psylaunch.launch_app('sublimetext', args=[_arg])

    def is_writable(self):
        """Check if this path is writable.

        Returns:
            (bool): writable status
        """
        return os.access(self.path, os.W_OK)

    def matches(self, other):
        """Test if the contents of this file matches another.

        Args:
            other (str): path to file to compare with

        Returns:
            (bool): whether files match
        """
        from .p_tools import get_path
        _path = get_path(other)
        return filecmp.cmp(self.path, _path)

    def read(self):
        """Read the text contents of this file."""
        from .p_tools import read_file
        return read_file(self.path)

    def read_yaml(self, catch=False):
        """Read the text contents of this file as yaml.

        Args:
            catch (bool): return empty dict on error

        Returns:
            (dict): yaml data
        """
        from .p_tools import read_yaml
        return read_yaml(self.path, catch=catch)

    def move_to(self, trg, force=False):
        """Move this file to somewhere else.

        Args:
            trg (str): new location
            force (bool): replace any existing file without confirmation
        """
        from .p_tools import get_path
        _trg = File(get_path(trg))
        if not force and _trg.exists():
            raise NotImplementedError
        shutil.move(self.path, _trg.path)

    def read_lines(self):
        """Read text lines of this file.

        Returns:
            (str list): list of lines
        """
        return [_line.strip('\n') for _line in self.read().split('\n')]

    def set_writable(self, writable=True):
        """Set writable state of this path.

        Args:
            writable (bool): writable state
        """
        _perms = 0o777 if writable else 0o444
        os.chmod(self.path, _perms)

    def test_dir(self):
        """Test this file's parent directory exists."""
        from .p_tools import test_path
        test_path(self.dir)

    def touch(self):
        """Touch this path."""
        from .p_tools import touch
        touch(self.path)

    def write_text(self, text, force=False):
        """Write text to this file.

        Args:
            text (str): text to write
            force (bool): overwrite existing file with no warning
        """
        from .p_tools import write_file
        _force = force
        if not force and self.exists():
            from psyhive import qt, icons
            _result = qt.raise_dialog(
                'Overwrite file?\n\n{}'.format(self.path),
                title='Confirm overwrite',
                icon=icons.EMOJI.find('Worried Face'),
                buttons=['Yes', 'Diff', 'Cancel'])
            if _result == 'Yes':
                _force = True
            elif _result == 'Diff':
                _tmp = File('{}/_{}_diff_tmp.{}'.format(
                    tempfile.gettempdir(), self.basename, self.extn))
                _tmp.write_text(text, force=True)
                _tmp.diff(self.path, check_extn=False)
            else:
                raise ValueError(_result)
        write_file(file_=self.path, text=text, force=_force)

    def write_yaml(self, data, force=False, mode='w'):
        """Write yaml data to file.

        Args:
            data (dict): data to write
            force (bool): replace existing without confirmation
            mode (str): write mode (default is w - replace)
        """
        from .p_tools import write_yaml
        write_yaml(file_=self.path, data=data, force=force, mode=mode)
