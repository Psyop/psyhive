"""Example module to test PyFile object."""


def test():
    """Some docs."""


def test2():
    pass


def args_test(arg1=False, arg2='a'):
    """Some docs.

    Args:
        arg1 (bool): first arg
        arg2 (str): second arg

    Returns:
        (bool): result
    """
    return True


def docs_example(arg1=False, arg2='a'):
    """Header.

    Description - this is
    a multi line.

    Args:
        arg1 (bool): first arg
            with new line
        arg2 (str): second arg

    Returns:
        (bool): result
            with new line

    Raises:
        (ValueError): cause
            with new line
    """


def missing_docs():
    pass


def missing_docs_args(arg1=False, arg2='a'):
    """Some docs."""


def missing_period():
    """Some docs"""
