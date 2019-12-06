"""General utilties relating to tank templates."""

from tank.platform import current_engine


def get_template(hint):
    """Get template matching the given hint.

    Args:
        hint (str): hint to match

    Returns:
        (TemplatePath): tank template
    """
    return current_engine().tank.templates[hint]
