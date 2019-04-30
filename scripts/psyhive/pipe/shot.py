"""Tools for managing shots."""

from psyhive.utils import Dir, find
from psyhive.pipe.project import Project


class Shot(Dir):
    """Represents a shot on disk."""

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path within the shot

        Raises:
            (ValueError): if path wasn't in a shot
        """
        self.project = Project(path)
        _tokens = self.project.rel_path(path).split('/')
        if (
                len(_tokens) < 3 or
                not _tokens[0] == 'sequences'):
            raise ValueError(path)
        _path = '/'.join([self.project.path] + _tokens[:3])
        super(Shot, self).__init__(_path)
        self.seq = _tokens[1]
        self.name = _tokens[2]

    def find_work_files(self):
        """Find work files within this shot.

        Returns:
            (WorkFile list): work files
        """
        from psyhive import pipe

        _work_files = []
        for _step_path in find(self.path, depth=1):
            _scenes_path = '{}/work/maya/scenes'.format(_step_path)
            for _path in find(_scenes_path, depth=1, type_='f'):
                try:
                    _work_file = pipe.WorkFile(_path)
                except ValueError:
                    continue
                _work_files.append(_work_file)
        return _work_files

    def get_work_file(
            self, step='animation', task='animation', dcc='maya', extn=None,
            ver_n=1):
        """Build a work file object from this shot.

        Args:
            step (str): work file step
            task (str): work file task
            dcc (str): work file dcc name
            extn (str): extension for workfile
            ver_n (int): work file version number

        Returns:
            (WorkFile): work file object
        """
        from psyhive import pipe
        _fmt = (
            '{self.path}/{step}/work/{dcc}/{scene_dir}'
            '{self.name}_{task}_v{ver_n:03d}.{extn}')
        _path = _fmt.format(
            self=self, step=step, task=task, dcc=dcc, ver_n=ver_n,
            scene_dir={
                'maya': 'scenes/',
                'nuke': '',
                'houdini': 'hip/'}[dcc],
            extn=extn or {'maya': 'ma', 'houdini': 'hip'}[dcc])
        return pipe.WorkFile(_path)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__, self.name)
