import unittest

from psyhive import tk2


class TestTk2(unittest.TestCase):

    def test(self):

        _path = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                 'animation/work/maya/scenes/dev0000_test_v001.ma')
        _work = tk2.TTWork(_path)
        _data = 'bladsasdasd'
        _work.cache_write(tag='blah', data=_data)
        assert _work.cache_read(tag='blah') == _data

        # Test get/set range
        _path = 'P:/projects/hvanderbeek_0001P/sequences/dev/dev9999'
        _shot = tk2.TTShot(_path)
        assert _shot.exists()
        for _rng in [(1001, 1010), (1001, 1020)]:
            print 'TESTING', _rng
            _shot.set_frame_range(_rng, use_cut=True)
            assert _shot.get_frame_range(use_cut=True) == _rng


if __name__ == '__main__':
    unittest.main()
