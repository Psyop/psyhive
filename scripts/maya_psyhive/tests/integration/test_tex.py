import unittest

from maya_psyhive import tex, open_maya as hom


class TestTex(unittest.TestCase):

    def test_read_shd(self):

        # Test assign se on read shd
        _sphere = hom.CMDS.polySphere()
        _shd = tex.read_shd(_sphere)
        assert _shd.shd == 'lambert1'
        assert _shd.get_se() == 'initialShadingGroup'


if __name__ == '__main__':
    unittest.main()
