import unittest

class TestPyFile(unittest.TestCase):

    def test_find(self):

        # Test depth flag
        _TEST_DIR = TMP+'/testing'
        touch(_TEST_DIR+'/test.txt')
        touch(_TEST_DIR+'/BLAH/test.txt')
        touch(_TEST_DIR+'/BLAH/BLEE/test.txt')
        assert len(find(_TEST_DIR, type_='f', depth=1)) == 1
        assert len(find(_TEST_DIR, type_='f', depth=2)) == 2
        assert len(find(_TEST_DIR, type_='f', depth=3)) == 3
