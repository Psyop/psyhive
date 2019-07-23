import operator
import os
import random
import shutil
import tempfile
import time
import unittest

from psyhive.utils import (
    passes_filter, apply_filter, abs_path, obj_write, obj_read, PyFile,
    store_result, restore_cwd, MissingDocs, rel_path, to_nice, wrap_fn,
    text_to_py_file, touch, get_single, find, Dir, File, get_time_t,
    get_owner, Cacheable, get_result_storer, Seq, store_result_on_obj,
    get_result_to_file_storer)

_TEST_DIR = '{}/psyhive/testing'.format(tempfile.gettempdir())


class TestCache(unittest.TestCase):

    def test_get_result_storer(self):

        class _Test(Cacheable):
            @get_result_storer()
            def get_rand(self, arg):
                return random.random()

            def __repr__(self):
                return '<Test:{}>'.format(id(self))
        _test = _Test()
        _val = _test.get_rand(1)
        assert _val == _test.get_rand(1)
        assert _val != _test.get_rand(2)
        assert _val != _Test().get_rand(1)

        # Test ignore_args
        @get_result_storer(ignore_args=True)
        def _test(a):
            return random.random()
        assert _test(1) == _test(2)

        # Test max age
        class _Test(object):
            cache_fmt = '{}/test/{{}}.cache'.format(tempfile.gettempdir())
            @get_result_to_file_storer(max_age=1)
            def blah(self):
                return random.random()
        _test = _Test()
        _val = _test.blah()
        assert _val == _test.blah()
        assert _val == _test.blah()
        time.sleep(2)
        assert _val != _test.blah()

    def test_store_result(self):

        @store_result
        def _test():
            return random.random()

        _result = _test()
        assert _test() == _result

    def test_store_result_on_obj(self):

        class _Test(object):
            @store_result_on_obj
            def test(self, vers=None):
                return random.random()
        _inst = _Test()
        _result = _inst.test()
        assert _inst.test() == _result
        assert _inst.test(vers=12123) == _result


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
        assert _args[0].type_ is None
        assert _args[0].default is None

        # Test None defaults
        _text = '''def test(a=None):
            pass
        '''
        _args = text_to_py_file(_text).find_def().find_args()
        assert _args[0].default is None

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
        assert rel_path(_path, root=_root) == (
            'psyhive/diary/y19/d0401/rip_icons.py')

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

        _path = '{}/psyhive/testing/owner_test.txt'.format(
            tempfile.gettempdir())
        touch(_path)
        self.assertEqual(get_owner(_path), os.environ['USER'])

    def test_set_writable(self):
        _test = File('{}/test.txt'.format(_TEST_DIR))
        print "TEST FILE", _test
        if _test.exists():
            _test.set_writable(True)
            _test.delete(force=True)
        _test.touch()
        assert _test.is_writable()
        print _test.set_writable(False)
        assert not _test.is_writable()
        _test.set_writable(True)
        _test.delete(force=True)


class TestSeq(unittest.TestCase):

    def test_contains(self):

        _seq = Seq('P:/dev0000_animation_persp_v004.%04d.jpg')
        _file = 'P:/dev0000_animation_persp_v004.1019.jpg'
        assert _seq.contains(_file)


class TestUtils(unittest.TestCase):

    def test_apply_filter(self):

        assert apply_filter(['a', 'b'], None) == ['a', 'b']

    def test_get_time_t(self):

        get_time_t(time.time())
        get_time_t(time.localtime())

    def test_obj_write(self):

        _path = '{}/unit_test/test.txt'.format(tempfile.gettempdir())
        if os.path.exists(_path):
            shutil.rmtree(os.path.dirname(_path))
        _obj = 'blah'
        obj_write(obj=_obj, file_=_path, verbose=1)
        assert obj_read(_path) == 'blah'

    def test_passes_filter(self):

        assert passes_filter('blah', '-ag', verbose=1)
        assert passes_filter('blah', 'ah')
        assert not passes_filter('blah', 'ag')
        assert passes_filter('test maya', 'test blah')
        assert not passes_filter('test maya', 'test +blah')

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

    def test_to_nice(self):

        assert to_nice('_get_flex_opts') == 'Get flex opts'

    def test_wrap_fn(self):

        def _test(a=1, b=2, c=3):
            return a, b, c
        assert wrap_fn(_test, b=3)() == (1, 3, 3)
        assert wrap_fn(_test, arg_to_kwarg='c')(4) == (1, 2, 4)

        # Test pass_data
        def _test(*args, **kwargs):
            return args, kwargs
        assert _test() == ((), {})
        assert _test(a=1) == ((), {'a': 1})
        assert wrap_fn(_test)() == ((), {})
        assert wrap_fn(_test, a=1)() == ((), {'a': 1})
        assert wrap_fn(_test)(a=1) == ((), {})
        assert wrap_fn(_test, arg_to_kwarg='test')(1) == ((), {'test': 1})
        assert wrap_fn(_test, pass_data=True)(a=1) == ((), {'a': 1})


if __name__ == '__main__':
    unittest.main()
