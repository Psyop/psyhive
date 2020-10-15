"""General icon utilities."""

from .ic_constants import EMOJI


def find(match, *args, **kwargs):
    """Find emoji matching the given name using the default emoji set.

    Args:
        match (str): name/filter to match

    Returns:
        (str): path to emoji image file
    """
    return EMOJI.find(match, *args, **kwargs)
