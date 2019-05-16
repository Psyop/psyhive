import operator
import os
import random
import shutil
import tempfile
import time
import unittest

from psyhive.utils import (
    passes_filter, apply_filter, abs_path, TMP, obj_write, obj_read, PyFile,
    store_result, restore_cwd, MissingDocs, rel_path, to_nice, wrap_fn,
    text_to_py_file, touch, get_single, find, Dir, File, get_time_t,
    get_owner)
from psyhive.utils.py_file.docs import MissingDocs


class TestPyFile(unittest.TestCase):

    def test(self):

        _example = abs_path('example.py', root=os.path.dirname(__file__))
        _py_file = PyFile(_example)
        assert _py_file.find_defs()
        assert _py_file.find_def('test')
        assert _py_file.find_def('test2')

        # Test docs
        _docs = _py_file.find_def('docs_example').get_docs()
        assert _docs.header == 'Header.'
        assert _docs.exc_type == 'ValueError'
        assert _docs.exc_desc == 'cause with new line'
        assert _docs.result_type == 'bool'
        assert _docs.result_desc == 'result with new line'
        assert len(_docs.args) == 2
        assert _docs.args[0].name == 'arg1'
        assert _docs.args[0].type_ == 'bool'
        assert _docs.args[0].desc == 'first arg with new line'
        assert _docs.args[1].name == 'arg2'
        assert _docs.args[1].type_ == 'str'
        assert _docs.args[1].desc == 'second arg'
        assert _docs.desc == 'Description - this is\na multi line.'

    def test_check_docs(self):

        _example = abs_path('example.py', root=os.path.dirname(__file__))
        _py_file = PyFile(_example)
        with self.assertRaises(MissingDocs):
            _py_file.find_def('missing_docs').check_docs()
        with self.assertRaises(MissingDocs):
            _py_file.find_def('missing_docs_args').check_docs()
        with self.assertRaises(MissingDocs):
            _py_file.find_def('missing_period').check_docs()

    def test_find_args(self):

        _text = '''def test(a, b, c=1, d=1):
            pass
        '''
        _args = text_to_py_file(_text).find_def().find_args()
        assert len(_args) == 4
        assert _args[3].name == 'd'
        assert _args[0].type_ == None
        assert _args[0].default == None

        # Test None defaults
        _text = '''def test(a=None):
            pass
        '''
        _args = text_to_py_file(_text).find_def().find_args()
        assert _args[0].default == None

        # Test tuple/dict/list defaults
        _text = '''def __test(a=(1, 2, 3), b=[1, 2, 3], c={'a': 1}):
            pass
        '''
        _def = text_to_py_file(_text).find_def()
        assert _def.find_arg('a').default == (1, 2, 3)
        assert _def.find_arg('b').default == [1, 2, 3]
        assert _def.find_arg('c').default == {'a': 1}


class TestPath(unittest.TestCase):

    def test(self):

        # Test cmp/hash
        _dir_a = Dir('/a/b/c')
        _dir_b = Dir('/a/b/c')
        assert _dir_a == _dir_b
        assert len({_dir_a, _dir_b}) == 1

        # Test override extn
        _file = File('/tmp/blah.ass.gz', extn='ass.gz')
        assert _file.extn == 'ass.gz'
        assert _file.basename == 'blah'

    @restore_cwd
    def test_abs_path(self):

        os.chdir('W:/Temp')
        assert abs_path('test.txt') == 'W:/Temp/test.txt'
        assert abs_path('./test.txt') == 'W:/Temp/test.txt'
        assert abs_path('./test.txt', root='K:/Temp') == 'K:/Temp/test.txt'
        assert abs_path('~/test.txt') == 'Z:/test.txt'
        assert abs_path('./test.txt', root='/a/b/c') == '/a/b/c/test.txt'
        assert abs_path('../test.txt', root='/a/b/c') == '/a/b/test.txt'

        _root = r'Z:/dev/global/code/pipeline/bootstrap/hv-test/python'
        _path = (
            r'Z:/dev/global/code/pipeline/bootstrap/hv-test/python\psyhive\\'
            r'diary\y19\d0401\rip_icons.py')
        assert rel_path(_path, root=_root) == 'psyhive/diary/y19/d0401/rip_icons.py'

        _path = 'file:///W:/Temp/icons/Emoji/icon.2469.png'
        assert abs_path(_path) == 'W:/Temp/icons/Emoji/icon.2469.png'

    def test_find(self):

        _test_dir = '{}/psyhive/testing/blah'.format(tempfile.gettempdir())
        _test_file = abs_path('{}/test.txt'.format(_test_dir))
        if os.path.exists(_test_dir):
            shutil.rmtree(_test_dir)
        touch(_test_file)
        assert get_single(find(_test_dir)) == _test_file
        assert get_single(find(_test_dir, full_path=False)) == 'test.txt'

    def test_get_owner(self):

        _path = '{}/psyhive/testing/owner_test.txt'.format(tempfile.gettempdir())
        touch(_path)
        self.assertEqual(get_owner(_path), os.environ['USER'])



class TestUtils(unittest.TestCase):

    def test_apply_filter(self):

        assert apply_filter(['a', 'b'], None) == ['a', 'b']

    def test_get_time_t(self):

        get_time_t(time.time())
        get_time_t(time.localtime())

    def test_obj_write(self):

        _path = '{}/unit_test/test.txt'.format(TMP)
        shutil.rmtree(os.path.dirname(_path))
        _obj = 'blah'
        obj_write(obj=_obj, path=_path, verbose=1)
        assert obj_read(_path) == 'blah'

    def test_passes_filter(self):

        assert passes_filter('blah', '-ag', verbose=1)
        assert passes_filter('blah', 'ah')
        assert not passes_filter('blah', 'ag')

        # Test key
        class _Test(object):
            def __init__(self, name):
                self.name = name
        _apple = _Test('apple')
        _banana = _Test('banana')
        _key = operator.attrgetter('name')
        assert passes_filter(_apple, 'apple', key=_key)
        _list = [_apple, _banana]
        assert apply_filter(_list, 'apple', key=_key) == [_apple]

        # Test case sensitive
        assert passes_filter('aaa', 'AAA')
        assert not passes_filter('aaa', 'AAA', case_sensitive=True)

        # Test quotes
        assert passes_filter('this is text', '"This is"')

    def test_store_result(self):

        @store_result
        def _test():
            return random.random()

        _result = _test()
        assert _test() == _result

    def test_to_nice(self):

        assert to_nice('_get_flex_opts') == 'Get flex opts'

    def test_wrap_fn(self):

        def _test(a=1, b=2, c=3):
            return a, b, c
        assert wrap_fn(_test, b=3)() == (1, 3, 3)
        assert wrap_fn(_test, arg_to_kwarg='c')(4) == (1, 2, 4)


if __name__ == '__main__':
    unittest.main()
