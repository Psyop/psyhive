import unittest

from psyhive import tk2
from maya_psyhive.shows import clashroyaleholi


class TestShows(unittest.TestCase):

    def test_clashroyaleholi(self):

        _path = ('P:/projects/hvanderbeek_0001P/sequences/test/test1911/'
                 'animation/work/maya/scenes/test1911_test_v001.ma')
        _work = tk2.get_work(_path)
        _dir = ('P:/projects/hvanderbeek_0001P/sequences/test/test1911/'
                'animation/output/animcache')
        assert clashroyaleholi._get_default_browser_dir(work=_work) == _dir

    def test_frasier(self):

        from maya_psyhive.shows import frasier


if __name__ == '__main__':
    unittest.main()
