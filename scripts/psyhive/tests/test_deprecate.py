import unittest

from psyhive import deprecate
from psyhive.utils import dev_mode


class TestDeprecate(unittest.TestCase):

    @_revert_dev_mode
    def test(self):

        with self.assertRaises(ValueError):
            deprecate.apply_deprecation('kash')

        if dev_mode():
            del os.environ['PSYOP_DEV']
        assert not dev_mode()
        deprecate.apply_deprecation("18/03/20 don't use this")

        with self.assertRaises(deprecate._DeprecationError):
            deprecate.apply_deprecation("18/03/20 don't use this")


def _revert_dev_mode(func):

    def _dev_mode_revert_func(*arg, **kwargs):

        _dev_mode = dev_mode()
        _result = func(*args, **kwargs)
        if not _dev_mode:
            del os.environ['PSYOP_DEV']
        else:
            os.environ['PSYOP_DEV'] = '1'
        assert dev_mode() == _dev_mode
        return _result
