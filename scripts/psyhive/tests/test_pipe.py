import unittest

from psyhive import pipe


class TestPipe(unittest.TestCase):

    def test(self):

        # Shade asset
        _path = (
            'P:/projects/hvanderbeek_0001P/assets/3D/character/archer/shade'
            '/output/shadegeo/shade_main/v068/maya/archer_shade_main_v068.mb')
        _asset = pipe.AssetFile(_path)
        assert _asset.step == 'shade'
        assert _asset.cpnt_name == 'main'
        assert _asset.asset_name == 'archer'
        assert _asset.task == 'shade'

        # Rig asset
        _path = (
            'P:/projects/clashclansbuild_35424P/assets/3D/prop/cannonBall/rig/'
            'output/rig/rig_main/v002/maya/cannonBall_main_rig.mb')
        _asset = pipe.AssetFile(_path)
        assert _asset.step == 'rig'
        assert _asset.cpnt_name == 'main'
        assert _asset.asset_name == 'cannonBall'
        assert _asset.task == 'rig'

        # Dynamic rig
        _path = (
            'P:/projects/cricketbillboa19_34774P/assets/3D/character/rose/'
            'rig/output/rig/dynamic_dynamic/v054/maya/'
            'rose_dynamic_dynamic_v054.mb')
        _asset = pipe.AssetFile(_path)
        assert _asset.step == 'rig'
        assert _asset.cpnt_name == 'dynamic'
        assert _asset.asset_name == 'rose'
        assert _asset.task == 'dynamic'

        # Bad paths
        _path = (
            'P:/projects/clashclansbuild_35424P/design/work/iirvin/ocean_geo/'
            'ocean_02.abc')
        with self.assertRaises(ValueError):
            _asset = pipe.AssetFile(_path)


if __name__ == '__main__':
    unittest.main()
