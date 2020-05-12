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


if __name__ == '__main__':
    unittest.main()
