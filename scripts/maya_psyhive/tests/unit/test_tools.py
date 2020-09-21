import unittest

from maya_psyhive.tools.m_batch_rerender import rerender


class TestTools(unittest.TestCase):

    def test_fkik_switcher(self):

        # Want to check missing yaml/elasticsearch/Qt
        from maya_psyhive.tools import fkik_switcher

    def test_frustrum_test_blast(self):

        from maya_psyhive.tools import blast_with_frustrum_check
        print 'FRUSTRUM TEST BLAST'

    def test_m_batch_rerender(self):

        assert rerender._layer_from_pass('masterLayer') == 'defaultRenderLayer'
        assert rerender._layer_from_pass('CHARS_bty') == 'rs_CHARS_bty'
