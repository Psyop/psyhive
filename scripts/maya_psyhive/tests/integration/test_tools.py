import os
import unittest

from maya import cmds
from pymel.core import nodetypes as nt

from psyhive import tk
from psyhive.utils import set_dev_mode, revert_dev_mode
from maya_psyhive import ref, tex, open_maya as hom
from maya_psyhive.utils import use_tmp_ns, del_namespace

from maya_psyhive.tools import (
    fkik_switcher, batch_cache, restore_img_plane, shader_bro)
from maya_psyhive.tools.batch_cache.tmpl_cache import CTTShotRoot
from maya_psyhive.tools.m_batch_rerender import rerender

_RIG_PATH = (
    'P:/projects/hvanderbeek_0001P/assets/3D/character/archer/rig/'
    'output/rig/rig_main/v016/maya/archer_rig_main_v016.mb')


class TestTools(unittest.TestCase):

    def test_batch_cache(self):

        _path = 'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000'
        _shot = CTTShotRoot(_path)
        _shot.read_work_files(force=True)

        _dialog = batch_cache.launch()
        _dialog.close()

    def test_batch_rerender(self):

        _path = ('P:/projects/hvanderbeek_0001P/assets/3D/character/'
                 'babyDragon/shade/output/shadegeo/shade_main/v019/maya/'
                 'babyDragon_shade_main_v019.mb')
        _ref = ref.obtain_ref(file_=_path, namespace='dragon')
        rerender._update_outputs_to_latest(refs=[_ref])

        # Test map abc to latest including rest cache
        _path = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                 'tracking/output/camcache/imagePlaneTest_renderCam/v053/'
                 'alembic/dev0000_imagePlaneTest_renderCam_v053.abc')
        assert rerender._get_latest_abc(_path)
        _path = ('P:/projects/hvanderbeek_0001P/assets/3D/character/'
                 'babyDragon/shade/output/shadegeo/shade_main/v019/maya/'
                 'babyDragon_shade_main_v019_restcache.abc')
        assert rerender._get_latest_abc(_path)

    def test_fkik_switcher(self):

        _dialog = fkik_switcher.launch_interface()
        _dialog.close()

        _ref = ref.obtain_ref(namespace='archer', file_=_RIG_PATH)
        _ctrl = _ref.get_node('Lf_armIk_Ctrl')
        _ctrl.select()
        _system = fkik_switcher.get_selected_system()
        _system.get_key_attrs()
        _system.apply_ik_to_fk()
        _system.apply_fk_to_ik()

    @revert_dev_mode
    def test_frustrum_test_blast(self):
        from maya_psyhive.tools.frustrum_test_blast import blast, remove_rigs

        set_dev_mode(False)

        # Test frustrum test
        _ref = ref.obtain_ref(namespace='archer_TMP', file_=_RIG_PATH,
                              class_=blast._Rig)
        assert isinstance(_ref, blast._Rig)
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
        _dialog.close()

    @revert_dev_mode
    @use_tmp_ns
    def test_restore_image_plane(self):
        set_dev_mode(False)
        print 'TEST RESTORE IMAGE PLANE'
        _path = ('P:/projects/hvanderbeek_0001P/sequences/dev/dev9999/'
                 'animation/work/maya/scenes/dev9999_imagePlaneTest_v001.ma')
        _work = tk.get_work(_path)
        _ref = ref.obtain_ref(file_=_work.path, namespace='restoreTest')
        assert not cmds.ls(type='imagePlane')
        for _path, _time_ctrl in [
                (('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_animCam/v053/'
                  'alembic/dev0000_imagePlaneTest_animCam_v053.abc'),
                 'animCam:AlembicTimeControl'),
                (('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_renderCam/v045/'
                  'alembic/dev0000_imagePlaneTest_renderCam_v045.abc'),
                 'renderCam:AlembicTimeControl'),
                (('P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/'
                  'tracking/output/camcache/imagePlaneTest_badCam/v053/'
                  'alembic/dev0000_imagePlaneTest_badCam_v053.abc'),
                 'badCam:AlembicTimeControl')]:
            _time_ctrl = _ref.get_node(_time_ctrl, strip_ns=False)
            print ' - TIME CTRL', _time_ctrl
            restore_img_plane(time_control=str(_time_ctrl), abc=_path)
        assert cmds.ls(type='imagePlane')

    @use_tmp_ns
    def test_shader_bro(self):

        _shader_bro = shader_bro.launch()

        # Test apply to selection
        _sphere = hom.CMDS.polySphere()
        assert tex.read_shd(_sphere) == 'lambert1'
        _shader_bro.ui.Asset.select_text('test')
        _shader_bro.ui.Task.select_text('sphere')
        _shader_bro.ui.Shader.select_text('blue_SG')
        _shader_bro.ui.ApplyToSelection.click()
        assert tex.read_shd(_sphere) == 'tmp:blue_SHD'
        _shader_bro.ui.Shader.select_text('blue_SG')

        # Test import shader
        _shader_bro.ui.Shader.select_text('pink_SG')
        assert not cmds.objExists('tmp:pink_SHD')
        _shader_bro.ui.ImportShader.click()
        assert cmds.objExists('tmp:pink_SHD')
        _shader_bro.close()

    @revert_dev_mode
    def test_shade_geo_for_rig(self):

        from maya_psyhive.tools import drive_shade_geo_from_rig

        set_dev_mode(False)

        _path = ('P:/projects/hvanderbeek_0001P/assets/3D/character/archer/'
                 'rig/output/rig/rig_main/v016/maya/archer_rig_main_v016.mb')
        _ref = ref.obtain_ref(file_=_path, namespace='archer_test')
        _ref.get_node('placer_Ctrl', class_=hom.HFnTransform).tz.set_val(10)
        _bbox = _ref.get_node('hairStrand_04_Geo', class_=hom.HFnMesh).bbox()
        _cache_set = nt.ObjectSet(_ref.get_node('bakeSet'))
        _n_refs = len(ref.find_refs())
        del_namespace(':tmp_archer_test')
        drive_shade_geo_from_rig(_cache_set)
        assert len(ref.find_refs()) == _n_refs
        _geo = hom.HFnMesh('tmp_archer_test:hairStrand_04_Geo')
        assert _geo.bbox().min == _bbox.min
        assert _geo.bbox().max == _bbox.max

    @revert_dev_mode
    @use_tmp_ns
    def test_write_image_plane(self):
        """Write image plane settings to output abc dir."""
        from maya_psyhive.tools import export_img_plane
        set_dev_mode(False)
        _img = (r"\\la1nas006\homedir\hvanderbeek\Desktop"
                r"\tumblr_p3gzfbykSP1rv4b7io1_1280.png")
        _abc_path = (
            'P:/projects/hvanderbeek_0001P/sequences/dev/dev0000/tracking/'
            'output/camcache/imagePlaneTest_renderCam/v047/alembic/'
            'dev0000_imagePlaneTest_renderCam_v047.abc')
        _abc = tk.get_output(_abc_path).find_latest()
        _presets = [
            '{}/{}'.format(_abc.parent().path, _filename)
            for _filename in ['camera.preset', 'imagePlane.preset']]

        for _preset in _presets:
            if os.path.exists(_preset):
                os.remove(_preset)

        _cam = hom.CMDS.camera()
        _img_plane = hom.CMDS.imagePlane(camera=_cam, fileName=_img)

        export_img_plane(camera=_cam.shp, abc=_abc.path)

        for _preset in _presets:
            assert os.path.exists(_preset)


if __name__ == '__main__':
    unittest.main()
