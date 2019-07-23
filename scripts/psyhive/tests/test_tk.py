import unittest

from psyhive import tk


class TestTk(unittest.TestCase):

    def test(self):

        _path = (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1/v013/alembic/'
            'dev0000_animation_archer1_v013.abc')
        assert tk.TTShotOutputName(_path).path == (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1')
        assert tk.TTShotOutputVersion(_path).path == (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1/v013')
        _path = (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/dev0000_fkikTest_v001.ma')
        _work = tk.TTMayaShotWork(_path)
        assert _work.path == _path
        assert _work == tk.get_work(_path)
        _path = (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/increments/dev0000_fkikTest_v001_001.ma')
        _inc = tk.TTMayaShotIncrement(_path)
        assert _inc.path == _path
        assert _inc.get_work() == tk.get_work(_path)
        assert _inc.get_work() == _work
        _path = ('P:/projects/hvanderbeek_0001P/assets/3D/character/archer/'
                 'rig/output/rig/rig_main/v003/maya/archer_rig_main_v003.mb')
        _out = tk.TTAssetOutputFile(_path)
        assert _out.version == 3

        # Check get metadata
        _path = (
            'P:/projects/hvanderbeek_0001P/assets/3D/character/ramon/rig/'
            'work/maya/scenes/ramon_dynamic_v003.mb')
        _work = tk.TTMayaAssetWork(_path)
        print _work.get_metadata()
        _path = (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/dev0000_aadvark_v034.ma')
        _work = tk.TTMayaShotWork(_path)
        assert _work.get_metadata()

    def test_get_output(self):

        for _path in [
                ('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                 'tracking/output/camcache/imagePlaneTest_renderCam/v045/'
                 'alembic/dev0000_imagePlaneTest_renderCam_v045.abc'),
                ('P:/projects/hvanderbeek_0001P/assets/3D/character/archer/'
                 'rig/output/rig/rig_main/v016/assembly/'
                 'archer_rig_main_v016.mb'),
        ]:
            assert tk.get_output(_path)

    def test_find_tank_app(self):

        tk.find_tank_app('fileops')
        tk.find_tank_app('psy-multi-fileops')

    def test_obtain_cacheable(self):

        _path = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                 'animation/work/maya/scenes/dev0000_aadvark_v034.ma')
        _work = tk.get_work(_path, catch=False)
        assert isinstance(_work, tk.TTMayaShotWork)
        _cacheable = tk.obtain_cacheable(_work)
        assert type(_cacheable).__name__ == '_CTTMayaShotWork'

        _path = (
            'P:/projects/hvanderbeek_0001P/assets/3D/character/archer/'
            'rig/output/rig/rig_main/v016/assembly/archer_rig_main_v016.mb')
        _output = tk.TTAssetOutputFile(_path)
        assert isinstance(_output, tk.TTAssetOutputFile)
        _cacheable = tk.obtain_cacheable(_output)
        assert type(_cacheable).__name__ == '_CTTAssetOutputFile'


if __name__ == '__main__':
    unittest.main()
