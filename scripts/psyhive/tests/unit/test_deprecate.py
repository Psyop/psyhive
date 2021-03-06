import unittest

from psyhive import deprecate
from psyhive.utils import dev_mode, revert_dev_mode, set_dev_mode


class TestDeprecate(unittest.TestCase):

    EXEC_SORT = 0.2

    @revert_dev_mode
    def test(self):

        with self.assertRaises(ValueError):
            deprecate.apply_deprecation('kash')

        set_dev_mode(False)
        assert not dev_mode()
        deprecate.apply_deprecation("18/03/20 don't use this")

        set_dev_mode(True)
        with self.assertRaises(deprecate._DeprecationError):
            deprecate.apply_deprecation("18/03/20 don't use this")
