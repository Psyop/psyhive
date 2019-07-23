import tempfile
import unittest

from psyhive.utils import touch, find


class TestPyFile(unittest.TestCase):

    def test_find(self):

        # Test depth flag
        _test_dir = '{}/testing'.format(tempfile.gettempdir())
        touch(_test_dir+'/test.txt')
        touch(_test_dir+'/BLAH/test.txt')
        touch(_test_dir+'/BLAH/BLEE/test.txt')
        assert len(find(_test_dir, type_='f', depth=1)) == 1
        assert len(find(_test_dir, type_='f', depth=2)) == 2
        assert len(find(_test_dir, type_='f', depth=3)) == 3
