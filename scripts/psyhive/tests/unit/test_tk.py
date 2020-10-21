import unittest

from psyhive import tk, pipe


class TestTk(unittest.TestCase):

    def test(self):

        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1/v013/alembic/'
            'dev0000_animation_archer1_v013.abc')
        assert tk.TTShotOutputName(_path).path == pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1')
        assert tk.TTShotOutputVersion(_path).path == pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'output/animcache/animation_archer1/v013')
        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/dev0000_fkikTest_v001.ma')
        _work = tk.TTMayaShotWork(_path)
        assert _work.path == _path
        assert _work == tk.get_work(_path)
        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/increments/dev0000_fkikTest_v001_001.ma')
        _inc = tk.TTMayaShotIncrement(_path)
        assert _inc.path == _path
        assert _inc.get_work() == tk.get_work(_path)
        assert _inc.get_work() == _work
        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/assets/3D/character/archer/'
            'rig/output/rig/rig_main/v003/maya/archer_rig_main_v003.mb')
        _out = tk.TTAssetOutputFile(_path)
        assert _out.version == 3

        # Check get metadata
        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/assets/3D/character/ramon/rig/'
            'work/maya/scenes/ramon_dynamic_v003.mb')
        _work = tk.TTMayaAssetWork(_path)
        print _work.get_metadata()
        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/animation/'
            'work/maya/scenes/dev0000_aadvark_v034.ma')
        _work = tk.TTMayaShotWork(_path)
        assert _work.get_metadata()

    def test_get_output(self):

        # Test create output
        for _path in [
                ('/hvanderbeek_0001P/sequences/dev/dev0000/'
                 'tracking/output/camcache/imagePlaneTest_renderCam/v045/'
                 'alembic/dev0000_imagePlaneTest_renderCam_v045.abc'),
                ('/hvanderbeek_0001P/assets/3D/character/archer/'
                 'rig/output/rig/rig_main/v016/assembly/'
                 'archer_rig_main_v016.mb'),
        ]:
            assert tk.get_output(pipe.PROJECTS_ROOT + _path)

        # Test output objects
        for _path in [
                '/hvanderbeek_0001P/sequences/dev/dev9999/'
                'animation/output/animcache/test_archer/v004/alembic/'
                'dev9999_test_archer_v004.abc',
                '/hvanderbeek_0001P/sequences/dev/dev9999/'
                'animation/output/render/test_masterLayer/v004/jpg/'
                'dev9999_test_masterLayer_v004.%04d.jpg',
        ]:
            _path = pipe.PROJECTS_ROOT + _path
            print _path
            _out = tk.get_output(_path)
            _latest = _out.find_latest()
            print _out
            assert not _out.is_latest()
            assert not _out == _latest
            assert _out.version < _latest.version
            print _latest
            print _out.find_work_file(verbose=0)
            assert (_out.map_to(_out.output_name_type) ==
                    _latest.map_to(_out.output_name_type))
            print

    def test_find_tank_app(self):

        tk.find_tank_app('fileops')
        tk.find_tank_app('psy-multi-fileops')

    def test_obtain_cacheable(self):

        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/sequences/dev/dev0000/'
            'animation/work/maya/scenes/dev0000_aadvark_v034.ma')
        _work = tk.get_work(_path, catch=False)
        assert isinstance(_work, tk.TTMayaShotWork)
        _cacheable = tk.obtain_cacheable(_work)
        assert type(_cacheable).__name__ == '_CTTMayaShotWork'

        _path = pipe.PROJECTS_ROOT + (
            '/hvanderbeek_0001P/assets/3D/character/archer/'
            'rig/output/rig/rig_main/v016/assembly/archer_rig_main_v016.mb')
        _output = tk.TTAssetOutputFile(_path)
        assert isinstance(_output, tk.TTAssetOutputFile)
        _cacheable = tk.obtain_cacheable(_output)
        assert type(_cacheable).__name__ == '_CTTAssetOutputFile'


if __name__ == '__main__':
    unittest.main()
