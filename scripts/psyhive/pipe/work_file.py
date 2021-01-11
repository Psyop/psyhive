"""Tools for managing work files."""

from psyhive.utils import File, abs_path

from .misc import read_ver_n
from .shot import Shot


class WorkFile(File):
    """Represents a workfile stored on disk."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to workfile
        """
        super(WorkFile, self).__init__(abs_path(path))
        del path
        self.shot = Shot(self.path)
        self.project = self.shot.project

        _b_tokens = self.basename.split('_')
        _d_tokens = self.shot.rel_path(self.path).split('/')

        if not _b_tokens[0] == self.shot.name:
            raise ValueError(self.path)

        # Read ver data
        self.ver = _b_tokens[-1]
        self.ver_n = read_ver_n(self.ver)
        assert self.path.count(self.ver) == 1
        self.ver_fmt = self.path.replace(self.ver, 'v{ver_n:03d}')

        self.step = _d_tokens[0]
        self.task = _b_tokens[1]
        self.dcc = _d_tokens[2]


class WorkFileInc(File):
    """Represents an increment of a workfile."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to work file inc
        """
        super(WorkFileInc, self).__init__(abs_path(path))
        del path
        self.shot = Shot(self.path)
        self.project = self.shot.project

        _b_tokens = self.basename.split('_')
        _d_tokens = self.shot.rel_path(self.path).split('/')

        if not _b_tokens[0] == self.shot.name:
            raise ValueError(self.path)
        if not _d_tokens[-2] == 'increments':
            raise ValueError(self.path)

        self.ver = _b_tokens[-2]
        self.ver_n = read_ver_n(self.ver)
        self.inc = _b_tokens[-1]
        self.inc_n = int(self.inc)

        self.step = _d_tokens[0]
        self.task = _b_tokens[1]
        self.dcc = _d_tokens[2]

    def get_work_file(self):
        """Get work file associated with this inc."""
        return self.shot.get_work_file(
            ver_n=self.ver_n, task=self.task, step=self.step, dcc=self.dcc,
            extn=self.extn)
