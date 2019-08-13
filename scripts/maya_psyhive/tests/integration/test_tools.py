import os
import unittest

from maya import cmds

from psyhive import tk
from maya_psyhive import ref
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import use_tmp_ns

from maya_psyhive.tools import (
    fkik_switcher, batch_cache, export_img_plane, restore_img_plane)
from maya_psyhive.tools.frustrum_test_blast.blast import _rig_in_cam, _Rig
from maya_psyhive.tools.batch_cache.tmpl_cache import CTTShotRoot
from maya_psyhive.tools.frustrum_test_blast import remove_rigs

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

    def test_fkik_switcher(self):

        _dialog = fkik_switcher.launch_interface()
        _dialog.ui.close()

        _ref = ref.obtain_ref(namespace='archer', file_=_RIG_PATH)
        _ctrl = _ref.get_node('Lf_armIk_Ctrl')
        _ctrl.select()
        _system = fkik_switcher.get_selected_system()
        _system.get_key_attrs()
        _system.apply_ik_to_fk()
        _system.apply_fk_to_ik()

    def test_frustrum_test_blast(self):

        # Test frustrum test
        _ref = ref.obtain_ref(namespace='archer_TMP', file_=_RIG_PATH,
                              class_=_Rig)
        assert isinstance(_ref, _Rig)
        _cam = hom.HFnCamera('persp')
        _pos = hom.HMatrix([
            0.95, 0.00, 0.31, 0.00, 0.08, 0.96, -0.26, 0.00, -0.29, 0.27,
            0.92, 0.00, -19.37, 25.40, 54.23, 1.00])
        _pos.apply_to(_cam)
        assert _rig_in_cam(rig=_ref, cam=_cam)
        _pos = hom.HMatrix([
            0.80, -0.00, -0.60, 0.00, -0.10, 0.98, -0.13, 0.00, 0.60, 0.16,
            0.79, 0.00, -16.33, 37.34, 109.80, 1.00])
        _pos.apply_to(_cam)
        assert not _rig_in_cam(rig=_ref, cam=_cam)

        # Test remove rigs ui
        _dialog = remove_rigs.launch([_ref], exec_=False)
        _dialog.close()

    def test_restore_image_plane(self):
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
            _time_ctrl = _ref.get_node(_time_ctrl)
            restore_img_plane(time_control=str(_time_ctrl), abc=_path)
        assert cmds.ls(type='imagePlane')

    @use_tmp_ns
    def test_write_image_plane(self):
        """Write image plane settings to output abc dir."""
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
