import unittest

from psyhive.tools import batch_rerender


class TestTools(unittest.TestCase):

    def test_batch_rerender(self):

        _dialog = batch_rerender.launch()
        _dialog.close()


if __name__ == '__main__':
    unittest.main()
