import random
import unittest

from psyhive import qt


class TestQt(unittest.TestCase):

    def test_combobox(self):

        _combo_box = qt.HComboBox()
        _combo_box.setObjectName('test')
        _datas = [random.random() for _ in range(10)]
        for _idx, _data in enumerate(_datas):
            print _idx, _data
            _combo_box.add_item(str(_data), data=_data)
        print _combo_box
        assert _combo_box.currentText() == str(_datas[0])
        assert _combo_box.selected_data() == _datas[0]
        _combo_box.select_data(_datas[4])
        assert _combo_box.selected_data() == _datas[4]
