"""Contains constant icon sets."""

from psyhive.utils import Collection, str_to_ints

from psyhive.icons.set_ import EmojiSet


EMOJI = EmojiSet(
    'W:/Temp/icons/Emoji/icon.%04d.png', frames=range(1, 2776))

ANIMALS = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1576-1672')])
FRUIT = Collection([
    EMOJI[_idx] for _idx in str_to_ints('1696-1722')])
