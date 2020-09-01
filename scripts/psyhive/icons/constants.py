"""Contains constant icon sets."""

import os

from psyhive.utils import Collection, str_to_ints, abs_path
from psyhive.icons.set_ import EmojiSet

_EMOJI_PATH_DEFAULT = abs_path(
    '{}/global/code/pipeline/bootstrap/psycons/icon_packs/EMOJI/'
    'icon.%04d.png'.format(os.environ.get('PSYOP_ROOT', 'P:/')))
_EMOJI_PATH = os.environ.get('PSYHIVE_ICONS_EMOJI', _EMOJI_PATH_DEFAULT)
EMOJI = EmojiSet(_EMOJI_PATH, frames=str_to_ints('0-2775'))

# Named icons
COPY = EMOJI.find('Spiral Notepad')
DELETE = EMOJI.find('Wastebasket')
BROWSER = EMOJI.find('Card Index Dividers')
EDIT = EMOJI.find('Pencil')
FILTER = EMOJI.find('Potable Water')
OPEN = EMOJI.find('Open File Folder')
REFRESH = EMOJI.find('Counterclockwise Arrows Button')
SAVE = EMOJI.find('Floppy Disk')

# Collections
ANIMALS = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1576-1672')])
FRUIT = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1696-1722')])
CATS = Collection([
    EMOJI[_idx] for _idx in str_to_ints('101-109,1585-1590')])
