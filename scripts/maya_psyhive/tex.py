"""Tools for managing texturing and shading."""

import os
import time

from maya import cmds

import six

from psyhive import qt
from psyhive.utils import get_single, lprint
from maya_psyhive import open_maya as hom
from maya_psyhive.utils import get_shp, load_plugin


class _BaseShader(object):
    """Base class for any shader."""

    col_attr = None
    out_col_attr = None

    def __init__(self, shd):
        """Constructor.

        Args:
            shd (str): shader node (eg. lambert1)
        """
        self.shd = hom.HFnDependencyNode(shd)

    def apply_texture(self, path):
        """Apply a texture file to this shader's main col attr.

        Args:
            path (str): texture file to apply
        """
        _file = get_single(cmds.listConnections(
            self.col_attr, destination=False, type='file'), catch=True)
        if not _file:
            assert not cmds.listConnections(self.col_attr, destination=False)
            _file = hom.CMDS.shadingNode('file', asShader=True)
            cmds.connectAttr(_file+'.outColor', self.col_attr)
        cmds.setAttr(_file+'.fileTextureName', path, type='string')
        cmds.setAttr(_file+'.colorSpace', 'linear', type='string')
        return _file

    def assign_to(self, geo):
        """Assign this shader to the given geo transform.

        Args:
            geo (str): geo transform
        """
        _se = self.get_se()
        if not _se:
            _se = self.create_se()
        print "SE", _se
        for _shp in cmds.listRelatives(geo, shapes=True):
            cmds.sets(_shp, edit=True, forceElement=_se)

    def create_se(self):
        """Create shading engine for this shader.

        Returns:
            (str): shading engine node
        """
        _name = str(self.shd).split(":")[-1]+"SG"
        _se = cmds.sets(
            name=_name, renderable=True, noSurfaceShader=True,
            empty=True)
        cmds.connectAttr(self.out_col_attr, _se+'.surfaceShader')
        return _se

    def get_se(self, verbose=0):
        """Get this shader's shading engine node.

        Args:
            verbose (int): print process data

        Returns:
            (str): shading engine node
        """
        _sets = cmds.listConnections(self.shd, type='objectSet', source=False)
        lprint('SETS', _sets, verbose=verbose)
        return get_single(_sets, catch=True)

    def read_texture(self, verbose=0):
        """Read the path to this shader's file texture (if any).

        Args:
            verbose (int): print process data

        Returns:
            (str|None): texture path
        """
        lprint("READING", self.col_attr, verbose=verbose)
        _conns = cmds.listConnections(
            self.col_attr, type='file', destination=False)
        lprint("CONNS", _conns, verbose=verbose)
        _file = get_single(_conns, catch=True)
        if _file:
            return cmds.getAttr(_file+'.fileTextureName')
        return None

    def set_col(self, col, verbose=0):
        """Set this node's main col attr.

        Args:
            col (str|tuple|QColor|HPlug): colour to apply (an existing
                path will be applied as a texture)
            verbose (int): print process data
        """
        if isinstance(col, hom.HPlug):
            lprint("CONNECTING PLUG", col, verbose=verbose)
            col.connect(self.col_attr)
            return
        if isinstance(col, six.string_types) and os.path.exists(col):
            lprint("APPLYING FILE TEXTURE", col, verbose=verbose)
            self.apply_texture(col)
            return

        # Apply colour as value
        _col = qt.get_col(col)
        lprint("APPLYING COLOUR", _col, verbose=verbose)
        cmds.setAttr(
            self.col_attr, *_col.to_tuple(mode='float'), type='double3')

    def __cmp__(self, other):
        if not hasattr(other, 'shd'):
            return cmp(self.shd, other)
        return cmp(self.shd, other.shd)

    def __hash__(self):
        return hash(self.shd)

    def __repr__(self):
        return '<{}:{}>'.format(type(self).__name__.strip('_'), self.shd)


class _AiAmbientOcclusion(_BaseShader):
    """Represents an aiAmbientOcclusion shader."""

    def __init__(self, shd):
        """Constructor.

        Args:
            shd (str): shader node (eg. lambert1)
        """
        super(_AiAmbientOcclusion, self).__init__(shd)
        self.col_attr = self.shd.plug('white')
        self.white = self.col_attr
        self.out_col_attr = self.shd.plug('outColor')


class _AiStandardSurface(_BaseShader):
    """Represents an aiStandardSurface shader."""

    def __init__(self, shd):
        """Constructor.

        Args:
            shd (str): shader node (eg. lambert1)
        """
        super(_AiStandardSurface, self).__init__(shd)
        self.col_attr = self.shd.plug('baseColor')
        self.out_col_attr = self.shd.plug('outColor')


class _Lambert(_BaseShader):
    """Represents an lambert shader."""

    def __init__(self, shd):
        """Constructor.

        Args:
            shd (str): shader node (eg. lambert1)
        """
        super(_Lambert, self).__init__(shd)
        self.col_attr = self.shd.plug('color')
        self.out_col_attr = self.shd.plug('outColor')


class _SurfaceShader(_BaseShader):
    """Represents an surface shader."""

    def __init__(self, shd):
        """Constructor.

        Args:
            shd (str): shader node (eg. lambert1)
        """
        super(_SurfaceShader, self).__init__(shd)
        self.col_attr = self.shd+'.outColor'
        self.out_col_attr = self.shd+'.outColor'


def ai_ambient_occlusion(name='aiAmbientOcclusion'):
    """Create an aiAmbientOcclusion shader.

    Args:
        name (str): node name

    Returns:
        (_AiAmbientOcclusion): shader
    """
    _shd = _AiAmbientOcclusion(cmds.shadingNode(
        'aiAmbientOcclusion', asShader=True, name=name))
    return _shd


def ai_standard_surface(name='aiStandardSurface', col=None):
    """Create an aiStandardSurface shader.

    Args:
        name (str): node name
        col (str|tuple|QColor): colour to apply

    Returns:
        (_AiStandardSurface): shader
    """
    load_plugin('mtoa')
    _shd = _AiStandardSurface(cmds.shadingNode(
        'aiStandardSurface', asShader=True, name=name))
    if col:
        _shd.set_col(col)
    return _shd


def build_texture_path(namespace, timestamp=True, extn='jpg'):
    """Build a texture path in the current workspace.

    Args:
        namespace (str): name for texture file
        timestamp (bool): include timestamp in path
        extn (str): file format

    Returns:
        (str): texture path
    """
    _tex_ws = cmds.workspace(fileRuleEntry='textures')
    _tex_dir = cmds.workspace(expandName=_tex_ws)
    return '{dir}/{base}{timestamp}.{extn}'.format(
        dir=_tex_dir, base=namespace, extn=extn,
        timestamp=time.strftime('_%H%M%S') if timestamp else '')


def connect_place_2d(node_, place=None):
    """Connect a place 2d texture node to the given shading node.

    Args:
        node_ (str): node to apply place 2d texture
        place (str): use an existing place2dTexture node

    Returns:
        (HFnDependencyNode): place2dTexture node
    """
    _node = hom.HFnDependencyNode(str(node_))

    # Get tex place node
    if place:
        _place = hom.HFnDependencyNode(place)
        assert _place.object_type() == "place2dTexture"
    else:
        _place = hom.CMDS.shadingNode("place2dTexture", asUtility=1)

    # Connect attrs with same name
    for _attr in [
            'coverage',
            'mirrorU',
            'mirrorV',
            'noiseUV',
            'offset',
            'repeatUV',
            'rotateFrame',
            'rotateUV',
            'stagger',
            'translateFrame',
            'uvCoord',
            'uvFilterSize',
            'vertexCameraOne',
            'vertexUvOne',
            'vertexUvThree',
            'vertexUvTwo',
            'wrapU',
            'wrapV',
    ]:
        if _node.has_attr(_attr):
            _place.plug(_attr).connect(_node.plug(_attr), force=True)

    # Connect attrs with different names
    for _src, _trg in [
            ("outUV", "uvCoord"),
            ("outUvFilterSize", "uvFilterSize"),
    ]:
        _place.plug(_src).connect(_node.plug(_trg), force=True)

    return _place


def find_shd(shd):
    """Build shader object from the given node name.

    Args:
        shd (str): node to search for

    Returns:
        (_BaseShader): shader object
    """
    _type = cmds.objectType(shd)
    if _type == 'lambert':
        return _Lambert(shd)
    elif _type == 'aiAmbientOcclusion':
        return _AiAmbientOcclusion(shd)
    elif _type == 'surfaceShader':
        return _SurfaceShader(shd)
    raise ValueError(_type)


def lambert(name='lambert', col=None):
    """Create a lambert shader.

    Args:
        name (str): node name
        col (str|tuple|QColor): colour to apply

    Returns:
        (_Lambert): shader
    """
    _shd = _Lambert(cmds.shadingNode(
        'lambert', asShader=True, name=name))
    if col:
        _shd.set_col(col)
    return _shd


def read_shd(shp, verbose=1):
    """Read shader from the given geo shape node.

    Args:
        shp (str): shape node to read
        verbose (int): print process data

    Returns:
        (_BaseShader): shader object
    """
    _shp = shp
    if cmds.objectType(_shp) == 'transform':
        _shp = get_shp(_shp)
    _se = get_single(cmds.listConnections(
        _shp, source=False, type='shadingEngine'), catch=True)
    if not _se:
        lprint('No shading engine found:', _shp, verbose=verbose)
        return None
    lprint('Shading engine:', _se, verbose=verbose > 1)
    _shd = get_single(cmds.listConnections(
        _se+'.surfaceShader', destination=False), catch=True)
    if not _shd:
        return None
    return find_shd(_shd)


def surface_shader(name='surfaceShader', col=None):
    """Create a surface shader.

    Args:
        name (str): node name
        col (str|tuple|QColor): colour to apply

    Returns:
        (_SurfaceShader): shader
    """
    _shd = _SurfaceShader(cmds.shadingNode(
        'surfaceShader', asShader=True, name=name))
    if col:
        _shd.set_col(col)
    return _shd
