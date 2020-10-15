"""Tools for managing icons."""

from .ic_constants import EMOJI
try:
    from .ic_constants import (
        COPY, EDIT, FILTER, REFRESH, DELETE,
        ANIMALS, CATS, FRUIT, BROWSER, OPEN, SAVE)
except ImportError:
    FRUIT = COPY = REFRESH = None
