"""Tools for managing assets."""

from psyhive.utils import File, find, abs_path, lprint
from psyhive.pipe.misc import read_ver_n
from psyhive.pipe.project import Project


class AssetFile(File):
    """Represents an asset file on disk."""

    def __init__(self, path, verbose=0):
        """Constructor.

        Args:
            path (str): path to asset file
            verbose (int): print process data
        """
        _path = abs_path(path)
        _extn = None
        if _path.endswith('.ass.gz'):
            _extn = 'ass.gz'
        super(AssetFile, self).__init__(_path, extn=_extn)
        del path
        self.project = Project(self.path)

        _d_tokens = self.project.rel_path(self.path).split('/')
        lprint('DTOKENS', _d_tokens, verbose=verbose)
        if len(_d_tokens) < 9:
            raise ValueError("Too short "+self.path)

        # Read ver
        self.ver = _d_tokens[8]
        self.ver_n = read_ver_n(self.ver)
        if not self.path.count(self.ver) in [1, 2]:
            raise RuntimeError(self.path)
        self.ver_fmt = self.path.replace(self.ver, 'v{ver_n:03d}')
        self.vers_path = '/'.join([self.project.path]+_d_tokens[:8])

        self.type_ = _d_tokens[2]
        self.asset_name = _d_tokens[3]
        self.step = _d_tokens[4]

        # Read component name
        _c_tokens = _d_tokens[7].split('_')
        self.fmt = _c_tokens[-1]
        self.cpnt_name = '_'.join(_c_tokens[:-1])

        _f_tokens = self.basename.split('.')[0].split('_')
        lprint('FTOKENS', _f_tokens, verbose=verbose)
        if len(_f_tokens) == 4:
            self.task = _f_tokens[1]
            self.cpnt_name = _f_tokens[2]
            if not _f_tokens[3] == self.ver:
                raise ValueError("Version mismatch "+self.path)
        elif len(_f_tokens) == 3:
            self.cpnt_name = _f_tokens[1]
            self.task = _f_tokens[2]
        else:
            raise ValueError(self.path)
        assert _f_tokens[0] == self.asset_name

    def find_latest(self):
        """Find latest version of this asset file.

        Returns:
            (AssetFile): latest version
        """
        _vers = find(self.vers_path, depth=1, type_='d', full_path=False)
        if not _vers:
            raise OSError("Missing asset "+self.vers_path)
        return AssetFile(self.ver_fmt.format(ver_n=int(_vers[-1][1:])))

    def is_latest(self):
        """Check if this is the latest version of this asset.

        Returns:
            (bool): whether latest
        """
        return self == self.find_latest()
