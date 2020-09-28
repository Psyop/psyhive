"""Tools for managing icons."""

from psyhive.icons.constants import EMOJI
try:
    from psyhive.icons.constants import (
        COPY, EDIT, FILTER, REFRESH, DELETE,
        ANIMALS, CATS, FRUIT, BROWSER, OPEN, SAVE,
    )
except ImportError:
    FRUIT = COPY = REFRESH = None
