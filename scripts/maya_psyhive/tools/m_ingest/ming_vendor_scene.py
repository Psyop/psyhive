"""Tools for managing vendor scenes."""

import time

from maya import cmds

from psyhive import tk2, host, pipe, qt
from psyhive.tools import ingest
from psyhive.utils import (
    File, lprint, store_result_to_file, get_result_to_file_storer,
    build_cache_fmt, get_single, get_time_t)

from maya_psyhive import ref, open_maya as hom, ui
from maya_psyhive.utils import DEFAULT_NODES

from .ming_remote import check_current_scene

_WAITING_ON_FARM_CACHE_TOKEN = 'waiting on farm cache 30/09/20'


class VendorScene(File, ingest.Ingestible):
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

    def check_workspace(self, force=False):
        """Check workspace for this shot has been created.

        Args:
            force (bool): create workspace without confirmation
        """
        _work = self.to_psy_work()
        _step = tk2.TTStepRoot(_work)
        if _step.exists():
            return
        tk2.TTRoot(_work).create_workspaces(force=force)

    def get_ingest_status(self):
        """Get ingestion status for this sequence.

        Returns:
            (str, bool): ingest status, ingestible
        """
        try:
            _work = self.to_psy_work()
        except ValueError as _exc:
            return _exc.message, False
        print ' - WORK', _work.path

        if _work.cache_read(ingest.INGESTED_TOKEN):
            return 'Already ingested', False

        if not _work.exists():
            return 'Ready to ingest', True
        _src = _work.cache_read('vendor_source')
        if _src and not _src == self.path:  # Check current source matches
            print ' - ORIGINAL SOURCE', _src
            return 'Already ingested from a different source', False
        elif not _src:
            print ' - APPLYING VENDOR SOURCE'
            _work.cache_write('vendor_source', self.path)

        if self.step in ['animation', 'previs']:
            print ' - CHECKING CAPTURE/CACHE'
            if not self.has_capture():
                return 'Needs capture', True
            if not self.has_capture_sg_version():
                if self.waiting_on_capture_sg_version():
                    return 'Waiting on capture version publish', False
                return 'Needs capture version publish', True
            if not self.has_cache():
                if self.waiting_on_cache():
                    return 'Waiting on farm cache', False
                return 'Needs cache', True
            print ' - CHECKED CAPTURE/CACHE'

        _work.cache_write(ingest.INGESTED_TOKEN, True)
        return 'Already ingested', False

    def get_ingest_issues(
            self, ignore_extn=False, ignore_dlayers=False,
            ignore_rlayers=False, ignore_multi_top_nodes=False,
            ignore_unknown=True):
        """Get ingest issues with this scene.

        Args:
            ignore_extn (bool): ignore file extension issues
            ignore_dlayers (bool): ignore display layer issues
            ignore_rlayers (bool): ignore render layer issues
            ignore_multi_top_nodes (bool): ignore issues with
                multiple top nodes
            ignore_unknown (bool): ignore unknown node issues

        Returns:
            (str list): list of problems with this scene
        """
        _issues = self._scene_read_ingest_issues()
        if ignore_extn:
            _issues = [_issue for _issue in _issues if not _issue.startswith(
                'File extension for animation should be ')]
        if ignore_multi_top_nodes:
            _issues = [_issue for _issue in _issues if not _issue.endswith(
                ' has multiple top nodes')]
        if ignore_dlayers:
            _issues = [_issue for _issue in _issues if not _issue.startswith(
                'Scene has display layers: ')]
        if ignore_rlayers:
            _issues = [_issue for _issue in _issues if not _issue.startswith(
                'Scene has render layers: ')]
        if ignore_unknown:
            _issues = [_issue for _issue in _issues if not _issue.startswith(
                'Scene has unknown nodes: ')]
        return _issues

    @get_result_to_file_storer(min_mtime=1601080442)
    def _scene_read_ingest_issues(self, force=False, verbose=0):
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
        self.scene_get_frame_range()

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

        elif self.step in ['animation', 'previz']:

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
            _psy_file = ingest.map_file_to_psy_asset(_ref.path)
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

    @get_result_to_file_storer(min_mtime=1601407139)
    def scene_get_frame_range(self):
        """Check if this scene's meshes match the model meshes."""
        host.open_scene(self.path, lazy=True, force=True)
        return host.t_range(int)

    def ingest(self, vendor=None, force=False, publish=True, capture=True,
               cache=True, cache_on_farm=True):
        """Ingest this file into psyop pipeline.

        Args:
            vendor (str): override vendor
            force (bool): lose unsaved changes without confirmation
            publish (bool): whether publish required
            capture (bool): whether capture required
            cache (bool): whether cache required
            cache_on_farm (bool): submit caches to qube
        """
        _comment = self.get_comment(vendor=vendor)
        self._ingest_check_work(force=force, comment=_comment)

        if self.step in ['rig']:
            if publish:
                self._ingest_check_publish(force=force)
        elif self.step in ['animation', 'previz']:
            self._ingest_check_sg_range()
            if capture:
                self._ingest_check_capture(force=force)
            if cache:
                self._ingest_check_cache(force=force, farm=cache_on_farm)
        else:
            raise ValueError(self.step)

    def _ingest_check_publish(self, force=False):
        """Check this scene has been published.

        Args:
            force (bool): lose unsaved changes without confirmation
        """
        raise NotImplementedError

    def _ingest_check_work(self, comment, force=False):
        """Check this file has a corresponding psyop work file.

        Args:
            comment (str): save comment
            force (bool): lose unsaved changes without confirmation
        """
        _work = self.to_psy_work()
        _src = _work.cache_read('vendor_source_file')
        if _work.exists() and _src:
            print 'THIS', self.path
            print 'SRC', _src
            if _src != self:
                raise RuntimeError('Source does not match')
            return

        print ' - INGEST WORK', _work.path

        print '   - COMMENT', comment
        if not force:
            qt.ok_cancel('Copy {} to pipeline?\n\n{}\n\n{}'.format(
                _work.step, self.path, _work.path))

        host.open_scene(self, force=force, lazy=True)

        # Update refs
        for _ref in qt.progress_bar(
                ref.find_refs(), 'Updating {:d} ref{}',
                stack_key='UpdateRefs'):
            self._ingest_check_ref(_ref)

        # Save to disk
        _work.save(comment=comment, safe=False, force=force)
        _work.cache_write(tag='vendor_source_file', data=self.path)

    def _ingest_check_ref(self, ref_):
        """Check reference.

        Args:
            ref_ (FileRef): reference to check
        """
        print 'CHECKING REF', ref_
        print ' - PATH', ref_.path
        if File(ref_.path).exists():

            try:
                _file = tk2.TTOutputFile(ref_.path)
            except ValueError:
                print ' - OFF PIPELINE'
                return

            if _file.is_latest():
                print ' - IS LATEST'
                return

            _file = _file.find_latest()

        else:

            _psy_file = ingest.map_file_to_psy_asset(ref_.path)
            _dlv_file = File('{}/{}'.format(
                self.dir, File(ref_.path).filename))
            _file = _psy_file or _dlv_file

        if not _file or not File(_file).exists():
            print ' - MISSING', _file
            raise RuntimeError('Missing file {}'.format(_file))

        print ' - UPDATING TO', _file
        assert File(_file).exists()
        ref_.swap_to(_file)

    def _ingest_check_sg_range(self, force=True):
        """Check shotgun range matching this scene file.

        Args:
            force (bool): update sg range without confirmation
        """
        _scn_rng = self.scene_get_frame_range()

        _work = self.to_psy_work()
        # if not _work.shot:
        #     return
        _shot = _work.get_shot()
        print 'CHECKING SG RANGE', _shot
        # _work.load(lazy=True)

        # _scn_rng = host.t_range(int)
        _shot_rng = _shot.get_frame_range(use_cut=False)
        print ' - RANGE scene={} shot={}'.format(_scn_rng, _shot_rng)
        if _scn_rng == _shot_rng:
            return

        if not force:
            qt.ok_cancel(
                'Update shotgun {} frame range to {:d}-{:d}?'.format(
                    _shot.name, int(_scn_rng[0]), int(_scn_rng[1])),
                title='Update shotgun range')
        _shot.set_frame_range(_scn_rng, use_cut=False)
        _shot.set_frame_range(_scn_rng, use_cut=True)  # For isaac
        print _shot.get_frame_range(use_cut=False)
        assert _shot.get_frame_range(use_cut=False) == _scn_rng

    def _ingest_check_capture(self, force=False):
        """Make sure this file has a corresponding psyop capture.

        Args:
            force (bool): lose unsaved changes without confirmation
        """
        _work = self.to_psy_work()

        # Build capture
        if not self.has_capture():

            print 'CAPTURING', _work.path
            _work.load(lazy=True)

            _cam = self.scene_get_cam()
            print ' - CAM', _cam
            assert _cam

            cmds.modelPanel(
                ui.get_active_model_panel(), edit=True, camera=_cam)

            tk2.capture_scene(force=True)

        # Submit version
        assert self.has_capture()
        _cap = _work.find_output_file(
            output_type='capture', extension='jpg', format_='jpg')
        if (
                not self.has_capture_sg_version() and
                not _cap.cache_read('submitted transgen')):
            _cap.submit_sg_version()
            assert _cap.cache_read('submitted transgen')

    def _ingest_check_cache(self, force=False, farm=True):
        """Check this file has been cached, executing cache if necessary.

        Args:
            force (bool): lose unsaved changes without confirmation
            farm (bool): cache on farm
        """
        if self.has_cache():
            return

        _work = self.to_psy_work()
        print 'CACHING', _work.path

        print ' - CACHE FMT', _work.cache_fmt
        if _work.cache_read(_WAITING_ON_FARM_CACHE_TOKEN):
            print ' - CACHE ALREADY SUBMITTED'
            return

        _work.load(lazy=True, force=force)

        assert not ref.find_refs(extn='abc')
        tk2.cache_scene(force=True, farm=farm)
        if farm:
            _work.cache_write(_WAITING_ON_FARM_CACHE_TOKEN, True)

    def has_capture(self, verbose=0):
        """Check if this file has a corresponding psyop capture.

        Args:
            verbose (int): print process data

        Returns:
            (bool): whether capture found
        """
        _work = self.to_psy_work()
        _cap = _work.find_output_file(
            output_type='capture', extension='jpg', format_='jpg')
        lprint(' - CHECKED HAS CAPTURE', verbose=verbose)
        return bool(_cap)

    def waiting_on_capture_sg_version(self):
        """Test if we're waiting on a capture transgen.

        ie. the capture transgen has been submitted to the farm.

        Returns:
            (bool): whether capture transgen has been submitted
        """
        if not self.has_capture():
            return False
        _work = self.to_psy_work()
        _cap = _work.find_output_file(
            output_type='capture', extension='jpg', format_='jpg')
        return _cap.cache_read('submitted transgen')

    def has_capture_sg_version(self):
        """Check if the capture has a shotgun version.

        Returns:
            (bool): whether sg version exists
        """
        _work = self.to_psy_work()
        _cap = _work.find_output_file(
            output_type='capture', extension='jpg', format_='jpg')
        return _cap.has_sg_version()

    def has_cache(self):
        """Check if this file has been cached.

        Returns:
            (bool): whether cache found
        """
        _work = self.to_psy_work()
        return bool(_work.find_output_files(
            extension='abc', output_type='animcache'))

    def waiting_on_cache(self):
        """Test if we're waiting on a farm cache.

        Returns:
            (bool): whether cache has been submitted
        """
        if self.has_cache():
            return False
        _work = self.to_psy_work()
        return _work.cache_read(_WAITING_ON_FARM_CACHE_TOKEN)

    def to_psy_work(self, verbose=0):
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

        elif self.step in ['animation', 'previz']:

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
                if not _src == self.path and not self.matches(_src):
                    print 'PREV FILE', _src
                    print 'MATCH', self.matches(_src)
                    _prev = VendorScene(_src)
                    _t_stamp = time.strftime(
                        '%m/%d/%y', get_time_t(_prev.mtime))
                    raise RuntimeError(
                        'already ingested from a different file '+_src)

        return _work
