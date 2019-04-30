"""Contains constant icon sets."""

from psyhive.utils import Collection, str_to_ints

from psyhive.icons.set_ import EmojiSet

EMOJI = EmojiSet(
    'P:/global/code/pipeline/bootstrap/psycons/icon_packs/EMOJI/icon.%04d.png',
    frames=str_to_ints('0-2775'))

COPY = EMOJI.find('Spiral Notepad')

ANIMALS = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1576-1672')])
FRUIT = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1696-1722')])
CATS = Collection([
    EMOJI[_idx] for _idx in str_to_ints('101-109,1585-1590')])
