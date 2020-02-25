"""Tools for managing ma files in vendor_in dir on frasier."""

from maya import cmds

from psyhive import host
from psyhive.utils import File, Dir, store_result_to_file, lprint

MOBURN_ROOT = 'P:/projects/frasier_38732V/production/vendor_in/Motion Burner'


class FrasierVendorMa(File):
    """Represents a vendor-in maya ascii file.

    This object allows the frame range to be cached to disk.
    """

    def __init__(self, path):
        """Constructor.

        Args:
            path (str): path to vendor-in ma file
        """
        super(FrasierVendorMa, self).__init__(path)
        _rel_path = Dir(MOBURN_ROOT).rel_path(self.dir)
        self.cache_fmt = '{}/data_cache/{}/{}_{{}}.cache'.format(
            MOBURN_ROOT, _rel_path, self.basename)

    def get_work(self, verbose=0):
        """Get work file object for this vendor file.

        Args:
            verbose (int): print process data

        Returns:
            (FrasierWork): matching work file
        """
        from . import frasier
        _tokens = self.basename.split('_')

        # Disposition
        if _tokens[0] == 'D':

            try:
                _, _char, _disp, _label, _iter = _tokens
            except ValueError:
                raise ValueError('Failed to parse '+self.path)

            assert _disp[0].isupper()
            assert _label[0].isupper()
            assert len(_iter) == 3
            lprint(' -', _char, _disp, _label, _iter, verbose=verbose)

            _task = 'd'+'xxx'.join([_disp, _label, _iter])

        # Vignette
        elif _tokens[0] == 'V':

            _, _char, _vignette, _desc, _iter = _tokens

            _task = 'v'+'xxx'.join([_vignette, _desc, _iter])

            assert _vignette[0].isupper()
            assert _desc[0].isupper()

        else:
            raise ValueError(_tokens[0])

        assert _char[0].isupper()
        assert _iter[0] == 'I'
        assert _iter[1:].isdigit()

        lprint(' - TASK', _task, verbose=verbose)
        _tmpl = 'maya_asset_work'
        _asset = frasier.ASSETS[_char]
        lprint(' - ASSET', _asset.path, verbose=verbose)
        _work = _asset.map_to(
            frasier.FrasierWork, Task=_task, version=1, Step='animation',
            extension='mb')

        return _work

    @store_result_to_file
    def get_range(self, force=False):
        """Get frame range of this ma file.

        Args:
            force (bool): force reread data

        Returns:
            (tuple): start/end frames
        """
        if not host.cur_scene() == self.path:
            cmds.file(self.path, open=True, prompt=False, force=force)
        return host.t_range()
