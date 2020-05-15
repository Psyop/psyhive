"""Tools for managing interfaces controlled by a single updating pixmap."""

import copy
import operator
import sys

from psyhive.utils import lprint, val_map, wrap_fn, dprint, abs_path, touch

from ..wrapper import QtWidgets, HPixmap, ORIGIN, QtCore
from ..misc import get_size, get_pixmap, get_p, safe_timer_event
from .ui_dialog import SETTINGS_DIR


class HPixmapUi2(QtWidgets.QDialog):
    """Base class for an interface with just an updating pixmap."""

    def __init__(self, size=(640, 640), base_col='red', fps=None, title=None,
                 mouse_tracking=False, parent=None, show=True):
        """Constructor.

        Args:
            size (QSize): interface size
            base_col (str): base colour for pixmap
            fps (float): frame rate (if declared timer is started)
            title (str): interface title
            mouse_tracking (bool): add mouse tracking (mouseMoveEvent)
            parent (QDialog): parent dialog
            show (bool): show interface on launch
        """
        from psyhive import host

        self.base_col = base_col
        self.frame = 0
        self.pause = False
        self.anims = []

        # Remove any existing intefaces
        _dialog_stack_key = type(self).__name__
        if _dialog_stack_key in sys.QT_DIALOG_STACK:
            sys.QT_DIALOG_STACK[_dialog_stack_key].delete()
        sys.QT_DIALOG_STACK[_dialog_stack_key] = self

        # Init base class
        _kwargs = {}
        _parent = parent or host.get_main_window_ptr()
        if _parent:
            _kwargs['parent'] = _parent
        super(HPixmapUi2, self).__init__(**_kwargs)

        # Set up interface/label
        self.setWindowTitle(title or type(self).__name__.strip('_'))
        _size = get_size(size)
        self.resize(_size)
        self._label = QtWidgets.QLabel(self)
        self._label.resize(_size)

        # Set up mouse tracking
        if mouse_tracking:
            self._label.setMouseTracking(True)
            self._label.mouseMoveEvent = self.mouseMoveEvent

        # Timer attrs
        self.pause = False
        self.timer = None
        if fps:
            self.timer = self.startTimer(1000.0/fps)
        assert self.timerEvent.SAFE_TIMER

        self.load_settings()
        self.redraw()
        if show:
            self.show()

    def delete(self):
        """Delete this interface."""
        for _mthd in (wrap_fn(self.closeEvent, None), self.deleteLater):
            try:
                _mthd()
            except RuntimeError:
                pass

    def redraw(self):
        """Redraw interface."""
        _size = self.size()
        self._pixmap = HPixmap(_size)
        self._pixmap.fill(self.base_col)
        self.update_pixmap(self._pixmap)
        self._label.setPixmap(self._pixmap)

    def update_pixmap(self, pix):
        """Update interface pixmap.

        Args:
            pix (QPixmap): pixmap to update
        """
        for _anim in self.anims:
            _anim.draw(pix)

    @property
    def settings(self):
        """Get settings object.

        Returns:
            (QSettings): settings
        """
        _name = type(self).__name__.strip('_')
        _settings_file = abs_path('{}/{}.ini'.format(SETTINGS_DIR, _name))
        touch(_settings_file)  # Check settings writable
        return QtCore.QSettings(
            _settings_file, QtCore.QSettings.IniFormat)

    def save_settings(self, verbose=0):
        """Save dialog settings.

        Args:
            verbose (int): print process data
        """
        dprint('SAVE SETTINGS', self.settings.fileName(), verbose=verbose)
        self.settings.setValue('window/pos', self.pos())
        lprint(' - SAVING POS', self.pos(), verbose=verbose)
        self.settings.setValue('window/size', self.size())
        lprint(' - SAVING SIZE', self.size(), verbose=verbose)

    def load_settings(self, verbose=1):
        """Read settings from disk.

        Args:
            verbose (int): print process data
        """
        dprint('LOAD SETTINGS', self.settings.fileName(), verbose=verbose)

        # Apply window settings
        _pos = self.settings.value('window/pos')
        if _pos:
            lprint(' - APPLYING POS', _pos, verbose=verbose)
            self.move(_pos)
        _size = self.settings.value('window/size')
        if _size:
            lprint(' - APPLYING SIZE', _size, verbose=verbose)
            self.resize(_size)

    def closeEvent(self, event):
        """Triggered by dialog close.

        Args:
            event (QEvent): event
        """
        self.save_settings()

    def keyPressEvent(self, event):
        """Executed on key press.

        Args:
            event (QEvent): key press event
        """
        if not event.text():
            pass
        elif event.text() == 's':
            print 'SAVE TEST'
            self._pixmap.save_test()
        elif event.text() in 'qx':
            print 'EXIT', event.text()
            self.delete()
        elif event.text() == 'p':
            self.pause = not self.pause
        super(HPixmapUi2, self).keyPressEvent(event)

    def resizeEvent(self, event):
        """Executed on resize.

        Args:
            event (QEvent): resize event
        """
        super(HPixmapUi2, self).resizeEvent(event)
        self._label.resize(self.size())
        self.redraw()

    @safe_timer_event
    def timerEvent(self, event, verbose=0):
        """Executed on timer tick.

        Args:
            event (QEvent): timer event
            verbose (int): print process data
        """
        super(HPixmapUi2, self).timerEvent(event)

        if self.pause:
            return
        self.frame += 1

        # Update anim
        if self.anims:
            lprint('DRAWING {:d} ANIMS'.format(
                len(self.anims)), verbose=verbose > 1)
            for _anim in copy.copy(self.anims):
                if _anim.has_completed():
                    lprint('[{:d}] COMPLETED {}'.format(self.frame, _anim),
                           verbose=verbose)
                    self.anims.remove(_anim)
                _anim.update()
            self.redraw()


def _key_lerp(fr_, key1, key2):
    """Linear interpolate between two keys.

    Args:
        fr_ (float): interpolation ratio
        key1 (Key): start key
        key2 (Key): end key

    Returns:
        (Key): interpolated key
    """
    return _AnimKey(
        time=val_map(fr_, out_min=key1.time, out_max=key2.time),
        rotate=val_map(fr_, out_min=key1.rotate, out_max=key2.rotate),
        scale=val_map(fr_, out_min=key1.scale, out_max=key2.scale),
        pos=get_p([
            val_map(fr_, out_min=key1.pos.x(), out_max=key2.pos.x()),
            val_map(fr_, out_min=key1.pos.y(), out_max=key2.pos.y()),
        ]))


class _AnimKey(object):
    """Represents a keyframe of animation data."""

    time = None

    def __init__(self, time, pos=ORIGIN, rotate=0.0, scale=1.0, func=None,
                 image=None):
        """Constructor.

        Args:
            time (int): key time
            pos (QPoint): key position
            rotate (float): key rotation
            scale (float): key scale
            func (fn): function to execute on key
            image (str|QPixmap): update anim image on this key
        """
        _time = int(round(time))
        if not round(time, 3) == _time:
            raise ValueError("Non-integer key time {}".format(time))
        self.time = _time
        self.pos = get_p(pos)
        self.rotate = rotate
        self.scale = scale
        self.func = func
        self.image = image

    def __repr__(self):
        return '<{}[{}]>'.format(
            type(self).__name__.strip('_'), self.time)


class Anim(object):
    """Represents an animation decribed by keyframes."""

    image = None
    src_image = None

    def __init__(self, image=None, src_image=None, label=None):
        """Constructor.

        Args:
            image (QPixmap|str): path to image to display
            src_image (str): path to source image - this allows
                a higher resolution image to be used on draw but
                scaling to be relative to the original image's size
            label (str): anim label (for debugging)
        """
        self.label = label
        self._set_image(image=image, src_image=src_image)
        self._start_size = self.image.size() if self.image else None

        self._dur = 0
        self._keys = {}
        self._timer = 0
        self.set_key(0)

    def _set_image(self, image, src_image=None):
        """Set current image of this anim.

        Args:
            image (str|QPixmap): image to apply
            src_image (str|QPixmap): source image (for enlarging)
        """
        self.image = get_pixmap(image) if image else None
        _src = src_image or image
        self.src_image = get_pixmap(_src) if _src else None

    def set_key(self, time, pos=ORIGIN, rotate=0.0, scale=1.0, func=None,
                image=None):
        """Apply a keyframe at the given time.

        Args:
            time (int): time to apply keyframe at
            pos (QPoint): key position
            rotate (float): key rotation
            scale (float): key scale
            func (fn): function to execute on key
            image (str|QPixmap): change image at this key
        """
        _key = _AnimKey(time=time, pos=pos, rotate=rotate, scale=scale,
                        func=func, image=image)
        self._keys[time] = _key
        self._dur = max(self._dur, time)

    def add_key(self, delay, pos=ORIGIN, rotate=0.0, scale=1.0, func=None,
                image=None):
        """Add a keyframe after the existing ones.

        Args:
            delay (int): number of frame after the current last frames
                to apply keyframe at
            pos (QPoint): key position
            rotate (float): key rotation
            scale (float): key scale
            func (fn): function to execute on key
            image (str|QPixmap): change image at this key
        """
        assert delay >= 0
        _time = max([_key.time for _key in self._keys.values()]) + delay
        self.set_key(time=_time, pos=pos, rotate=rotate, scale=scale,
                     func=func, image=image)

    def draw(self, pix, verbose=0):
        """Draw this anim on the given pixmap.

        Args:
            pix (QPixmap): pixmap to draw on
            verbose (int): print process data
        """

        # Get key or key transition
        _key = _s_key = _e_key = None
        _keys = sorted(self._keys.values(), key=operator.attrgetter('time'))
        lprint('GETTING KEY AT', self._timer, _keys, verbose=verbose)
        for _idx, _o_key in enumerate(_keys):
            if self._timer < _o_key.time:
                continue
            elif self._timer == _o_key.time:
                _key = _o_key
                break
            else:
                assert _o_key.time <= self._timer
                _s_key = _o_key
                _e_key = _keys[_idx+1]

        # Get key values
        if _key:  # Exact keyframe
            if _key.func:
                _key.func()
            if _key.image:
                self._set_image(_key.image)
        else:  # Interpolate keyframe
            _fr = val_map(self._timer, in_min=_s_key.time, in_max=_e_key.time)
            lprint(
                ' - KEY {:d} -> {:d} ({:.02f})'.format(
                    _s_key.time, _e_key.time, _fr),
                verbose=verbose)
            _key = _key_lerp(_fr, key1=_s_key, key2=_e_key)
            assert _key.time == self._timer
        lprint(
            ' - RESULT pos=({:d}, {:d}) rotate={:02f} scale={:02f}'.format(
                _key.pos.x(), _key.pos.y(), _key.rotate, _key.scale),
            verbose=verbose)

        # Draw image
        if self.image:
            _pix = HPixmap(self.src_image)
            _size = self._start_size * _key.scale
            _pix = _pix.resize(_size.width(), _size.height())
            if _key.rotate:
                _pix = _pix.rotated(_key.rotate)
            pix.add_overlay(_pix, pos=_key.pos, anchor='C')
            lprint(' - DRAW ANIM', _key.pos, self.image, _pix.size(),
                   verbose=verbose)

    def get_dur(self):
        """Get duration of this animation.

        Returns:
            (int): number of frames
        """
        return self._dur

    def get_t_remaining(self):
        """Get time remaining for this anim.

        Returns:
            (int): number of frames remaining
        """
        return self._dur - self._timer

    def has_completed(self):
        """Test if this anim has completed.

        Returns:
            (bool): completed
        """
        return self._timer >= self._dur

    def update(self, verbose=0):
        """Update this anim (applied once per clock tick).

        Args:
            verbose (int): print process data
        """
        self._timer += 1

    def __repr__(self):
        return '<{}{}:{:d}>'.format(
            type(self).__name__,
            '({})'.format(self.label) if self.label else '',
            self.get_dur())
