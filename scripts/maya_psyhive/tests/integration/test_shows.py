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

        _abc = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                'animation/output/animcache/aadvark_archer1/v039/alembic/'
                'dev0000_aadvark_archer1_v039.abc')
        assert clashroyaleholi._get_abc_range_from_sg(_abc) == (1005, 1015)
        _abc = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev9999/'
                'animation/output/animcache/test_archer/v005/alembic/'
                'dev9999_test_archer_v005.abc')
        assert clashroyaleholi._get_abc_range_from_sg(_abc) is None


if __name__ == '__main__':
    unittest.main()
