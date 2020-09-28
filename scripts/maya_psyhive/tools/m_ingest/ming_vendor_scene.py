"""Tools for managing vendor scenes."""

import time

from maya import cmds

from psyhive import tk2, host, pipe
from psyhive.tools import ingest
from psyhive.utils import (
    File, lprint, store_result_to_file, get_result_to_file_storer,
    build_cache_fmt, get_single, get_time_t)

from maya_psyhive import ref, open_maya as hom
from maya_psyhive.utils import DEFAULT_NODES

from .ming_remote import check_current_scene


class VendorScene(File):
    """Represents a scene file from an outsource vendor."""

    def __init__(self, file_):
        """Constructor.

        Args:
            file_ (str): path to scene file
        """
        super(VendorScene, self).__init__(file_)
        _data = ingest.parse_basename(self.basename)
        self.tag, self.step, self.version = _data
        self.ver_n = int(self.version[1:])
        self.cache_fmt = build_cache_fmt(self.path, level='project')

    @property
    def mtime(self):
        """Get delivery time.

        Returns:
            (float): delivery time
        """
        raise NotImplementedError

    def get_ingest_status(self):
        """Get ingestion status for this sequence.

        Returns:
            (str, bool): ingest status, ingestable
        """
        try:
            _work = self.to_psy_work()
        except ValueError as _exc:
            return _exc.message, False
        print ' - WORK', _work.path

        if _work.cache_read(ingest.INGESTED_TOKEN):
            return 'Already ingested', False

        _issues = self.scene_get_ingest_issues()
        if _issues:
            return 'Ingestion issues', False

        if not _work.exists():
            return 'Ready to ingest', True

        if self.step in ['animation', 'previs']:
            raise NotImplementedError('check blast/cached')

        # Check current source matches
        _src = _work.cache_read('vendor_source')
        if _src and not _src == self.path:
            print ' - ORIGINAL SOURCE', _src
            return 'Already ingested from a different source', False
        elif not _src:
            print ' - APPLYING VENDOR SOURCE'
            _work.cache_write('vendor_source', self.path)

        _work.cache_write(ingest.INGESTED_TOKEN, True)
        return 'Already ingested', False

    @get_result_to_file_storer(min_mtime=1601080442)
    def scene_get_ingest_issues(self, force=False, verbose=0):
        """Get a list of sanity check issues for this file.

        An empty list means that no issues were found.

        Args:
            force (bool): lose unsaved changes without confirmation
            verbose (int): print process data

        Returns:
            (str list): list of issues
        """
        lprint('CHECKING ISSUES', self.path, verbose=verbose)
        host.open_scene(self.path, lazy=True, force=True)
        _issues = []

        _issues += check_current_scene(show_dialog=False, verbose=0)

        # Check for work
        _work = self.to_psy_work()
        _latest = _work.find_latest()
        if _latest and _latest.ver_n > _work.ver_n:
            _issues.append('later version exists')

        # Apply sanity checks
        if self.step == 'rig':

            if not self.scene_has_bake_set():
                _issues.append('missing bake set')
            if not self.scene_has_valid_meshes():
                _issues.append('no valid meshes')
            if not self.scene_meshes_match_model():
                _issues.append('meshes do not match model')

        elif self.step in ['animation', 'previs']:

            if not self.scene_get_cam():
                _issues.append('no cam found')

            # _refs = self.scene_get_refs(force=force)
            # for _namespace, _file in _refs.items():
            #     _issues += self._get_ref_issues(
            #         namespace=_namespace, file_=_file, refs=_refs,
            #         verbose=verbose)

        else:
            raise ValueError(self.step)

        return _issues

    @get_result_to_file_storer(min_mtime=1596664734)
    def scene_get_cam(self):
        """Get render cam from this scene.

        Returns:
            (str): camera name
        """
        print 'READING CAM', self.path
        host.open_scene(self.path, lazy=True, force=True)

        _cam_rig = None
        for _ref in ref.find_refs():

            if 'cam' not in _ref.path.lower():
                continue

            if _ref.is_loaded():
                _cam_rig = _ref
                continue

            print ' - REF', _ref.path
            _psy_file = ingest.map_ref_to_psy_asset(_ref.path)
            print ' - PSY FILE', _psy_file
            if _psy_file:
                _ref.swap_to(_psy_file)
                assert not _cam_rig
                _cam_rig = _ref

        _cams = [
            _cam for _cam in hom.find_nodes(class_=hom.HFnCamera)
            if _cam not in DEFAULT_NODES]
        print ' - CAMS', _cams

        print ' - CAM RIG', _cam_rig
        if not len(_cams) == 1 and _cam_rig:
            _cam_rig_cam = _cam_rig.get_tfm('animCam')
            return str(_cam_rig_cam)

        _cam = get_single(_cams)
        return str(_cam)

    @store_result_to_file
    def scene_get_refs(self, force=False):
        """Find reference paths in this scene.

        Args:
            force (bool): lose unsaved changes without confirmation

        Returns:
            (dict): dict of reference namespaces/paths
        """
        host.open_scene(self.path, lazy=True, force=True)
        _refs = {}
        for _ref in ref.find_refs():
            _refs[_ref.namespace] = _ref.path
        return _refs

    @store_result_to_file
    def scene_has_bake_set(self):
        """Check if this file has a bake set.

        Returns:
            (bool): whether bake set
        """
        host.open_scene(self.path, lazy=True, force=True)
        return cmds.objExists('bakeSet')

    @store_result_to_file
    def scene_has_valid_meshes(self):
        """Check if this scene has valid meshes for export."""
        raise NotImplementedError

    @store_result_to_file
    def scene_meshes_match_model(self):
        """Check if this scene's meshes match the model meshes."""
        raise NotImplementedError

    def ingest(self, force=False, publish=True, capture=True, cache=True):
        """Ingest this file into psyop pipeline.

        Args:
            force (bool): lose unsaved changes without confirmation
            publish (bool): whether publish required
            capture (bool): whether capture required
            cache (bool): whether cache required
        """
        raise NotImplementedError
        # assert not self.scene_get_ingest_issues()
        # self._check_work(force=force)

        # if self.step in ['rig']:
        #     if publish:
        #         self._check_publish(force=force)
        # elif self.step in ['animation']:
        #     if capture:
        #         self._check_capture(force=force)
        #     if cache:
        #         self._check_cache(force=force)
        # else:
        #     raise ValueError

    def to_psy_work(self, verbose=1):
        """Get psyop work file for this scene.

        Args:
            verbose (int): print process data

        Returns:
            (TTWork): work file
        """
        if self.step == 'rig':

            # Find asset
            _asset = tk2.TTAsset('{}/assets/3D/prop/{}'.format(
                pipe.cur_project().path, self.tag))
            if not _asset.exists():
                _asset = ingest.map_tag_to_asset(self.tag)
            assert _asset.exists()
            _work = _asset.map_to(
                tk2.TTWork, dcc='maya', Step=self.step,
                Task=self.step, extension='mb', version=self.ver_n)

        elif self.step in ['animation', 'previs']:

            lprint(' - TAG', self.tag, verbose=verbose)
            _shot = ingest.map_tag_to_shot(self.tag)
            if not _shot:
                raise RuntimeError('Failed to map {} to shot'.format(
                    self.tag))
            lprint(' - SHOT', _shot, verbose=verbose)
            _work = _shot.map_to(
                tk2.TTWork, dcc='maya', Step=self.step,
                Task=self.step, extension='ma', version=self.ver_n)

        else:
            raise ValueError('Unhandled step '+self.step)

        assert _work.version == self.ver_n

        if _work.exists():
            _src = _work.cache_read('vendor_source_file')
            if _src:
                if not _src == self.path:
                    _prev = VendorScene(_src)
                    _t_stamp = time.strftime(
                        '%m/%d/%y', get_time_t(_prev.mtime))
                    raise RuntimeError(
                        'already ingested from a different file '+_t_stamp)

        return _work
