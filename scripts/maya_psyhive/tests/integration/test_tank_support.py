import os
import unittest

from maya import cmds
from pymel.core import nodetypes as nt

from psyhive import tk2, pipe
from psyhive.utils import File, revert_dev_mode, set_dev_mode

from maya_psyhive import ref, open_maya as hom
from maya_psyhive.utils import use_tmp_ns, del_namespace, set_namespace

from maya_psyhive import tank_support

_DEV_PROJ = pipe.find_project('hvanderbeek')
_RIG_PATH = (_DEV_PROJ.path + '/assets/3D/character/archer/rig/'
             'output/rig/rig_main/v016/maya/archer_rig_main_v016.mb')
_SHADE_PATH = (_DEV_PROJ.path + '/assets/3D/character/archer/'
               'shade/output/shadegeo/shade_main/v092/maya/'
               'archer_shade_main_v092.mb')


class TestTankSupport(unittest.TestCase):

    EXEC_SORT = 0.5

    @revert_dev_mode
    def test_aistandin(self):

        from maya_psyhive.tank_support import ts_aistandin
        set_dev_mode(False)

        _abc = (
            _DEV_PROJ.path + '/sequences/dev/dev9999/'
            'animation/output/animcache/test_archer/v004/alembic/'
            'dev9999_test_archer_v004.abc')
        _standin = File(
            _DEV_PROJ.path + '/assets/3D/character/archer/'
            'shade/output/shadegeo/shade_main/v092/aistandin/'
            'archer_shade_main_v092.ma')

        # Test build standin output (for Publish Tool)
        _standin.delete(force=True)
        assert not _standin.exists()
        tank_support.build_aistandin_output(output=_standin.path)
        assert _standin.exists()

        # Test apply abc to standin output (for Asset Manager)
        _shade = ref.obtain_ref(_standin.path, namespace='ais_test')
        tank_support.apply_abc_to_shade_aistandin(
            namespace=_shade.namespace, abc=_abc)
        assert _shade.get_node('AISShape').plug('dso').get_val() == _abc

        # Test build standin from shade (for clash holiday)
        _shade_path = (
            _DEV_PROJ.path + '/assets/3D/character/archer/shade/'
            'output/shadegeo/shade_main/v092/maya/archer_shade_main_v092.mb')
        _shade = ref.obtain_ref(namespace='archer_SHD', file_=_shade_path)
        _standin = tank_support.build_aistandin_from_shade(
            archive=_abc, shade=_shade, deferred=False)
        assert _standin.shp.plug('dso').get_val() == _abc

        # Test read sg range
        _abc = (_DEV_PROJ.path + '/sequences/dev/dev0000/'
                'animation/output/animcache/aadvark_archer1/v039/alembic/'
                'dev0000_aadvark_archer1_v039.abc')
        assert ts_aistandin._get_abc_range_from_sg(_abc) == (1005, 1015)

    def test_frustrum_test_blast(self):

        from maya_psyhive.tank_support.ts_frustrum_test_blast import (
            blast, remove_rigs)

        # Test frustrum test
        _ref = ref.obtain_ref(namespace='archer_TMP', file_=_RIG_PATH,
                              class_=blast._BlastRigRef)
        assert isinstance(_ref, blast._BlastRigRef)
        _cam = hom.HFnCamera('persp')
        _pos = hom.HMatrix([
            0.95, 0.00, 0.31, 0.00, 0.08, 0.96, -0.26, 0.00, -0.29, 0.27,
            0.92, 0.00, -19.37, 25.40, 54.23, 1.00])
        _pos.apply_to(_cam)
        assert blast._rig_in_cam(rig=_ref, cam=_cam)
        _pos = hom.HMatrix([
            0.80, -0.00, -0.60, 0.00, -0.10, 0.98, -0.13, 0.00, 0.60, 0.16,
            0.79, 0.00, -16.33, 37.34, 109.80, 1.00])
        _pos.apply_to(_cam)
        assert not blast._rig_in_cam(rig=_ref, cam=_cam)

        # Test remove rigs ui
        _dialog = remove_rigs.launch([_ref], exec_=False)
        assert len(_dialog.ui.List.all_items()) == 1
        assert len(_dialog.ui.List.selectedItems()) == 1
        _dialog.close()

    @use_tmp_ns
    def test_restore_image_plane(self):

        # Test restore via psyhive
        _path = (_DEV_PROJ.path + '/sequences/dev/dev9999/'
                 'animation/work/maya/scenes/dev9999_imagePlaneTest_v001.ma')
        _work = tk2.TTWork(_path)
        _ref = ref.obtain_ref(file_=_work.path, namespace='restoreTest')
        assert not cmds.ls(type='imagePlane')
        for _path, _time_ctrl in [
                ((_DEV_PROJ.path + '/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_animCam/v053/'
                  'alembic/dev0000_imagePlaneTest_animCam_v053.abc'),
                 'animCam:AlembicTimeControl'),
                ((_DEV_PROJ.path + '/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_renderCam/v045/'
                  'alembic/dev0000_imagePlaneTest_renderCam_v045.abc'),
                 'renderCam:AlembicTimeControl'),
                ((_DEV_PROJ.path + '/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_badCam/v053/'
                  'alembic/dev0000_imagePlaneTest_badCam_v053.abc'),
                 'badCam:AlembicTimeControl')]:
            _time_ctrl = _ref.get_node(_time_ctrl, strip_ns=False)
            tank_support.restore_img_plane(
                time_control=str(_time_ctrl), abc=_path)
        assert cmds.ls(type='imagePlane')

        # Test restore via asset manager
        set_namespace(":")
        _path = (_DEV_PROJ.path + '/sequences/dev/dev0000/'
                 'animation/output/camcache/fishTest_renderCam/v001/'
                 'alembic/dev0000_fishTest_renderCam_v001.abc')
        tk2.reference_publish(_path)

    def test_shade_geo_from_rig(self):

        _path = (_DEV_PROJ.path + '/assets/3D/character/archer/'
                 'rig/output/rig/rig_main/v016/maya/archer_rig_main_v016.mb')
        _ref = ref.obtain_ref(file_=_path, namespace='archer_test')
        _ref.get_node('placer_Ctrl', class_=hom.HFnTransform).tz.set_val(10)
        _bbox = _ref.get_node('hairStrand_04_Geo', class_=hom.HFnMesh).bbox()
        _cache_set = nt.ObjectSet(_ref.get_node('bakeSet'))
        _n_refs = len(ref.find_refs())
        del_namespace(':tmp_archer_test')
        tank_support.drive_shade_geo_from_rig(_cache_set, verbose=1)
        assert len(ref.find_refs()) == _n_refs
        _geo = hom.HFnMesh('tmp_archer_test:hairStrand_04_Geo')
        assert _geo.bbox().min == _bbox.min
        assert _geo.bbox().max == _bbox.max

    def test_shader_outputs(self):

        from maya_psyhive.tank_support import ts_shaders

        _abc = (
            _DEV_PROJ.path + '/sequences/dev/dev9999/'
            'animation/output/animcache/test_archer/v004/alembic/'
            'dev9999_test_archer_v004.abc')
        _standin = tk2.TTOutputFile(
            _DEV_PROJ.path + '/assets/3D/character/archer/'
            'shade/output/shadegeo/shade_main/v092/aistandin/'
            'archer_shade_main_v092.ma')
        _shaders = _standin.map_to(extension='mb', format='shaders')
        _yml = _standin.map_to(extension='yml', format='shaders')

        # Test build standin output (for Publish Tool)
        for _out in [_shaders, _standin, _yml]:
            _out.delete(force=True)
        assert not _standin.exists()
        tank_support.build_shader_outputs(output=_standin.path)
        for _out in [_shaders, _standin, _yml]:
            assert _out.exists()

        # Test apply abc to standin output (for Asset Manager)
        _shade = ref.obtain_ref(_standin.path, namespace='ais_test')
        tank_support.apply_abc_to_shade_aistandin(
            namespace=_shade.namespace, abc=_abc)
        assert _shade.get_node('AISShape').plug('dso').get_val() == _abc

        # Test build standin from shade (for clash holiday)
        _shade_path = (
            _DEV_PROJ.path + '/assets/3D/character/archer/shade/'
            'output/shadegeo/shade_main/v092/maya/archer_shade_main_v092.mb')
        _shade = ref.obtain_ref(namespace='archer_SHD', file_=_shade_path)
        _standin = tank_support.build_aistandin_from_shade(
            archive=_abc, shade=_shade, deferred=False)
        assert _standin.shp.plug('dso').get_val() == _abc

        # Test read sg range
        _abc = (_DEV_PROJ.path + '/sequences/dev/dev0000/'
                'animation/output/animcache/aadvark_archer1/v039/alembic/'
                'dev0000_aadvark_archer1_v039.abc')
        assert ts_shaders._get_abc_range_from_sg(_abc) == (1005, 1015)

    def test_build_shader_outputs(self):
        _path = (_DEV_PROJ.path + '/assets/3D/character/test/'
                 'shade/output/shadegeo/sphere_main/v036/shaders/'
                 'test_sphere_main_v036.mb')
        tank_support.build_shader_outputs(_path, force=True)

    def test_read_mesh_data(self):
        for _name in ['bakeSet', 'testSphere']:
            if cmds.objExists(_name):
                cmds.delete(_name)
        _sphere = hom.CMDS.polySphere(name='testSphere')
        _sphere.add_to_set('bakeSet')
        _data = tank_support.read_mesh_data()
        assert _data['testSphere'] == {
            'uv_sets': ['map1'], 'poly_count': 400, 'vtx_count': 382}
        print _data

    @use_tmp_ns
    def test_write_image_plane(self):
        """Write image plane settings to output abc dir."""
        _img = (r"\\la1nas006\homedir\hvanderbeek\Desktop"
                r"\tumblr_p3gzfbykSP1rv4b7io1_1280.png")
        _abc_path = (
            _DEV_PROJ.path + '/sequences/dev/dev0000/tracking/'
            'output/camcache/imagePlaneTest_renderCam/v047/alembic/'
            'dev0000_imagePlaneTest_renderCam_v047.abc')
        _abc = tk2.TTOutputFile(_abc_path).find_latest()
        _presets = [
            '{}/{}'.format(_abc.parent().path, _filename)
            for _filename in ['camera.preset', 'imagePlane.preset']]

        for _preset in _presets:
            if os.path.exists(_preset):
                os.remove(_preset)

        _cam = hom.CMDS.camera()
        _img_plane = hom.CMDS.imagePlane(camera=_cam, fileName=_img)

        tank_support.export_img_plane(camera=_cam.shp, abc=_abc.path)

        for _preset in _presets:
            assert os.path.exists(_preset)


if __name__ == '__main__':
    unittest.main()
