"""Tools for managing the base class for any ingestible."""

import time

from psyhive.utils import get_time_t, get_time_f

from .ing_utils import vendor_from_path


class Ingestible(object):
    """Base class for any ingestible item."""

    path = None

    def get_comment(self, vendor):
        """Get publish/cache comment for this file.

        Args:
            vendor (str): override vendor

        Returns:
            (str): comment
        """
        _vendor = vendor or vendor_from_path(self.path)
        return 'From {} {}'.format(
            _vendor,
            time.strftime('%m/%d/%y', get_time_t(self.mtime)))

    @property
    def mtime(self):
        """Retrieve delivery date from source file path.

        Returns:
            (float): delivery date
        """
        for _token in reversed(self.path.split('/')):
            _date_str = _token.split('_')[0]
            for _t_fmt in ['%Y-%m-%d']:
                try:
                    _mtime = time.strptime(_date_str, _t_fmt)
                except ValueError:
                    pass
                else:
                    return get_time_f(_mtime)
        raise ValueError('Failed to read delivery date {}'.format(self.path))
