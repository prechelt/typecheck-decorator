# Most of this file is from the lower part of Dmitry Dvoinikov's
# http://www.targeted.org/python/recipes/typecheck3000.py
# reworked into py.test tests

import collections
import functools
import random

import typecheck as tc
from .testhelper import expected

############################################################################

def test_FixedSequenceChecker1():
    @tc.typecheck
    def foo(a: (int, str)=(1, "!"), *, k: tc.optional(())=()) -> (str, ()):
        return a[1], k

    assert foo() == ("!", ())
    assert foo((2, "x")) == ("x", ())
    assert foo(k=()) == ("!", ())
    assert foo((33, "44"), k=()) == ("44", ())
    assert foo([3, "4"]) == ("4", ())
    assert foo(k=[]) == ("!", [])
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: (1,)")):
        foo((1,))
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: (1, 2)")):
        foo(k=(1, 2))


def test_FixedSequenceChecker2():
    @tc.typecheck
    def foo(a: []=[], *, k: tc.optional([])=None) -> ([], tc.optional([])):
        return a, k

    assert foo() == ([], None)
    assert foo([]) == ([], None)
    assert foo(k=[]) == ([], [])
    assert foo([], k=[]) == ([], [])
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: ()")):
        foo(())
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: (1,)")):
        foo((1,))
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ()")):
        foo(k=())
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: (1,)")):
        foo(k=(1,))


def test_FixedSequenceChecker3():
    @tc.typecheck
    def foo(*args) -> (int, str):
        return args

    foo(1, "2") == 1, "2"
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: (1, 2)")):
        foo(1, 2)
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: (1, '2', None)")):
        foo(1, "2", None)
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: (1,)")):
        foo(1)


def test_FixedSequenceChecker4():
    @tc.typecheck
    def foo(*, k: tc.optional([[[[lambda x: x % 3 == 1]]]])=[[[[4]]]]):
        return k[0][0][0][0]

    assert foo() % 3 == 1
    assert foo(k=[[[[1]]]]) % 3 == 1
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: [[[[5]]]]")):
        foo(k=[[[[5]]]])


def test_FixedSequenceChecker5():
    @tc.typecheck
    def foo(a: collections.UserList([str, collections.UserList])):
        return a[1][1]

    assert foo(collections.UserList(["aha!", collections.UserList([3, 4, 5])])) == 4
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: ")):
        assert foo(["aha!", collections.UserList([3, 4, 5])]) == 4


def test_FixedMappingChecker_dict():
    @tc.typecheck
    def foo(arg: dict(a=int, b=str)):
        return arg["a"] + len(arg["b"])

    assert foo(dict(a=1, b="hugo")) == 5
    with expected(tc.InputParameterError("foo() has got an incompatible value for arg: ")):
        assert foo(dict(aaa=1, b="hugo")) == 5
    with expected(tc.InputParameterError("foo() has got an incompatible value for arg: ")):
        assert foo(dict(a=1.0, b="hugo")) == 5
    with expected(tc.InputParameterError("foo() has got an incompatible value for arg: ")):
        assert foo(dict(a=1, b="hugo", c=None)) == 5
    with expected(tc.InputParameterError("foo() has got an incompatible value for arg: ")):
        assert foo(dict(b="hugo")) == 4


def test_FixedMappingChecker_namedtuple():
    Mynt = collections.namedtuple("MyNT", "a b")

    @tc.typecheck
    def foo1(arg: dict(a=int, b=str)):
        if isinstance(arg, tuple):
            return arg.a + len(arg.b)
        else:
            return arg["a"] + len(arg["b"])

    assert foo1(Mynt(a=1, b="hugo")) == 5
    assert foo1(dict(a=1, b="hugo")) == 5


def test_CallableChecker1():
    @tc.typecheck
    def foo(a: callable, *, k: callable) -> callable:
        return a(k(lambda: 2))

    x = lambda x: x
    assert foo(x, k=x)() == 2


def test_CallableChecker2():
    class NumberToolset:
        @classmethod
        @tc.typecheck
        def is_even(cls, value: int) -> bool:
            return value % 2 == 0

        @staticmethod
        @tc.typecheck
        def is_odd(value: int) -> bool:
            return not NumberToolset.is_even(value)

    @tc.typecheck
    def foo(a: NumberToolset.is_even=0) -> NumberToolset.is_odd:
        return a + 1

    assert foo() == 1
    assert foo(2) == 3
    with expected(tc.InputParameterError("is_even() has got an incompatible value for value: 1.0")):
        foo(1.0)


def test_CallableChecker3():
    @tc.typecheck
    def foo(x=None) -> type(None):
        return x

    assert foo() is None
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: ''")):
        foo("")


def test_OptionalChecker1():
    @tc.typecheck
    def foo(b: bool) -> bool:
        return not b

    assert foo(True) is False
    assert foo(False) is True
    with expected(tc.InputParameterError("foo() has got an incompatible value for b: 0")):
        foo(0)

    @tc.typecheck
    def foo(*, b: tc.optional(bool)=None) -> bool:
        return b

    assert foo(b=False) is False
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: None")):
        foo()


def test_OptionalChecker2():
    not_none = lambda x: x is not None
    with expected(tc.TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @tc.typecheck
        def foo(a: not_none=None):
            return a

    @tc.typecheck
    def foo(a: tc.optional(not_none)=None):  # note how optional overrides the not_none
        return a

    assert foo() is None
    assert foo(None) is None
    with expected(tc.TypeCheckSpecificationError("the default value for k is incompatible with its typecheck")):
        @tc.typecheck
        def foo(*, k: not_none=None):
            return k

    @tc.typecheck
    def foo(*, k: tc.optional(not_none)=None):  # note how optional overrides the not_none
        return k

    assert foo() is None
    assert foo(k=None) is None

    @tc.typecheck
    def foo(x=None) -> not_none:
        return x

    with expected(tc.ReturnValueError("foo() has returned an incompatible value: None")):
        foo()

    @tc.typecheck
    def foo(x=None) -> tc.optional(not_none):  # note how optional overrides the not_none
        return x

    assert foo() is None
    assert foo(None) is None


def test_hasattrs1():
    class FakeIO:
        def write(self):
            pass

        def flush(self):
            pass

    @tc.typecheck
    def foo(a: tc.hasattrs("write", "flush")):
        pass

    foo(FakeIO())
    del FakeIO.flush
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: <")):
        foo(FakeIO())


def test_hasattrs2():
    assert tc.hasattrs("__class__")(int) and tc.hasattrs("__class__").check(int)
    assert not tc.hasattrs("foo")(int) and not tc.hasattrs("foo").check(int)


def test_has1():
    assert tc.re("^abc$")("abc")
    assert not tc.re("^abc$")(b"abc")
    assert not tc.re(b"^abc$")("abc")
    assert tc.re(b"^abc$")(b"abc")
    assert tc.re(b"^foo\x00bar$")(b"foo\x00bar")
    assert not tc.re(b"^foo\x00bar$")(b"foo\x00baz")
    assert tc.re("^abc")("abc\n")
    assert tc.re(b"^abc")(b"abc\n")
    assert not tc.re("^abc$")("abc\n")
    assert not tc.re(b"^abc$")(b"abc\n")
    assert not tc.re("^abc$")("abcx")
    assert not tc.re(b"^abc$")(b"abcx")


def test_has2():
    @tc.typecheck
    def foo(*, k: tc.re("^[0-9A-F]+$")) -> tc.re("^[0-9]+$"):
        return "".join(reversed(k))

    assert foo(k="1234") == "4321"
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ''")):
        foo(k="")
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: 1")):
        foo(k=1)
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: DAB")):
        foo(k="BAD")


def test_has3():
    @tc.typecheck
    def foo(*, k: (tc.re("^1$"), [tc.re("^x$"), tc.re("^y$")])):
        return k[0] + k[1][0] + k[1][1]

    assert foo(k=("1", ["x", "y"])) == "1xy"
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ('2', ['x', 'y'])")):
        foo(k=("2", ["x", "y"]))
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ('1', ['X', 'y'])")):
        foo(k=("1", ["X", "y"]))
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ('1', ['x', 'Y'])")):
        foo(k=("1", ["x", "Y"]))


def test_has4():
    russian = "\u0410\u0411\u0412\u0413\u0414\u0415\u0401\u0416\u0417\u0418\u0419\u041a" \
              "\u041b\u041c\u041d\u041e\u041f\u0420\u0421\u0422\u0423\u0424\u0425\u0426" \
              "\u0427\u0428\u0429\u042c\u042b\u042a\u042d\u042e\u042f\u0430\u0431\u0432" \
              "\u0433\u0434\u0435\u0451\u0436\u0437\u0438\u0439\u043a\u043b\u043c\u043d" \
              "\u043e\u043f\u0440\u0441\u0442\u0443\u0444\u0445\u0446\u0447\u0448\u0449" \
              "\u044c\u044b\u044a\u044d\u044e\u044f"
    assert len(russian) == 66

    @tc.typecheck
    def foo(s: tc.re("^[{0}]$".format(russian))):
        return len(s)

    for c in russian:
        assert foo(c) == 1
    with expected(tc.InputParameterError("foo() has got an incompatible value for s: @")):
        foo("@")


def test_has5():
    @tc.typecheck
    def numbers_only_please(s: tc.re("^[0-9]+$")):
        pass

    numbers_only_please("123")
    with expected(tc.InputParameterError("numbers_only_please() has got an incompatible value for s: 123")):
        numbers_only_please("123\x00HUH?")


def test_has6():
    assert tc.re("^123$")("123") and tc.re("^123$").check("123")
    assert not tc.re("^123$")("foo") and not tc.re("^123$").check("foo")


def test_seq_of_simple():
    @tc.typecheck
    def foo_s(x: tc.seq_of(int)) -> tc.seq_of(float):
        return list(map(float, x))

    assert foo_s([]) == []
    assert foo_s(()) == []
    assert foo_s([1, 2, 3]) == [1.0, 2.0, 3.0]
    with expected(tc.InputParameterError("foo_s() has got an incompatible value for x: ['1.0']")):
        foo_s(["1.0"])
    with expected(tc.InputParameterError("foo_s() has got an incompatible value for x: 1")):
        foo_s(1)


def test_list_of_simple():
    @tc.typecheck
    def foo_l(x: tc.list_of(int)) -> tc.list_of(float):
        return list(map(float, x))

    assert foo_l([]) == []
    with expected(tc.InputParameterError("foo_l() has got an incompatible value for x: ()")):
        foo_l(())
    assert foo_l([1, 2, 3]) == [1.0, 2.0, 3.0]
    with expected(tc.InputParameterError("foo_l() has got an incompatible value for x: ['1.0']")):
        foo_l(["1.0"])
    with expected(tc.InputParameterError("foo_l() has got an incompatible value for x: 1")):
        foo_l(1)


def test_seq_of_complex():
    @tc.typecheck
    def foo(x: tc.seq_of((tc.re("^[01]+$"), int))) -> bool:
        return functools.reduce(lambda r, e: r and int(e[0], 2) == e[1],
                                x, True)

    assert foo([("1010", 10), ("0101", 5)])
    assert not foo([("1010", 10), ("0111", 77)])


def test_seq_of_with_optional():
    assert tc.seq_of(tc.optional(tc.re("^foo$")))(["foo", None, "foo"]) and \
           tc.seq_of(tc.optional(tc.re("^foo$"))).check(["foo", None, "foo"])
    assert not tc.seq_of(tc.optional(tc.re("^foo$")))(["123", None, "foo"]) and \
           not tc.seq_of(tc.optional(tc.re("^foo$"))).check(["foo", None, "1234"])


def test_seq_of_UserList():
    assert tc.seq_of(int)([4, 5])
    assert tc.seq_of(int)(collections.UserList([4, 5]))


def test_seq_of_str_with_simple_str():
    assert not tc.seq_of(str)("A sequence of strings, but not a seq_of(str)")


def test_seq_of_checkonly():
    almost_ints = list(range(1000)) + ["ha!"] + list(range(1001, 2001))
    non_gotchas = (tc.seq_of(int, checkonly=9)(almost_ints) +
                   tc.seq_of(int, checkonly=10)(almost_ints) +
                   tc.seq_of(int, checkonly=11)(almost_ints))
    assert non_gotchas >= 2  # should fail about once every 40000 runs
    almost_ints = list(range(1000)) + 10 * ["ha!"] + list(range(1010, 2001))
    non_gotchas = (tc.seq_of(str, checkonly=8)(almost_ints) +
                   tc.seq_of(str, checkonly=9)(almost_ints) +
                   tc.seq_of(str, checkonly=10)(almost_ints))
    assert non_gotchas <= 1  # should fail almost never


def test_map_of_simple():
    @tc.typecheck
    def foo(x: tc.map_of(int, str)) -> tc.map_of(str, int):
        return {v: k for k, v in x.items()}

    assert foo({}) == {}
    assert foo({1: "1", 2: "2"}) == {"1": 1, "2": 2}
    with expected(tc.InputParameterError("foo() has got an incompatible value for x: []")):
        foo([])
    with expected(tc.InputParameterError("foo() has got an incompatible value for x: {'1': '2'}")):
        foo({"1": "2"})
    with expected(tc.InputParameterError("foo() has got an incompatible value for x: {1: 2}")):
        foo({1: 2})


def test_map_of_complex():
    @tc.typecheck
    def foo(*, k: tc.map_of((int, int), [tc.re("^[0-9]+$"), tc.re("^[0-9]+$")])):
        return functools.reduce(lambda r, t: r and str(t[0][0]) == t[1][0] and
                                             str(t[0][1]) == t[1][1],
                                k.items(), True)

    assert foo(k={(1, 2): ["1", "2"], (3, 4): ["3", "4"]})
    assert not foo(k={(1, 3): ["1", "2"], (3, 4): ["3", "4"]})
    assert not foo(k={(1, 2): ["1", "2"], (3, 4): ["3", "5"]})
    with expected(tc.InputParameterError(
            "foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3, 4): ['3', 'x']}")):
        foo(k={(1, 2): ["1", "2"], (3, 4): ["3", "x"]})
    with expected(tc.InputParameterError(
            "foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3,): ['3', '4']}")):
        foo(k={(1, 2): ["1", "2"], (3,): ["3", "4"]})
    with expected(tc.InputParameterError(
            "foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3, 4.0): ['3', '4']}")):
        foo(k={(1, 2): ["1", "2"], (3, 4.0): ["3", "4"]})


def test_map_of_with_optional():
    assert tc.map_of(int, tc.optional(str))({1: "foo", 2: None}) and \
           tc.map_of(int, tc.optional(str)).check({1: "foo", 2: None})
    assert not tc.map_of(int, tc.optional(str))({None: "foo", 2: None}) and \
           not tc.map_of(int, tc.optional(str)).check({None: "foo", 2: None})


def test_map_of_OrderedDict():
    assert tc.map_of(int, str)(collections.OrderedDict())


def test_map_of_checkonly():
    def probably_int(i):
        return i if random.random() > 0.25 else str(i)

    def probably_str(i):
        return str(i) if random.random() > 0.25 else i

    correct = 0
    # test-check 20 random dictionaries with random violations:
    for i in range(20):
        mydict = dict()
        numbers = random.sample(range(1000000), 8)  # are variable and all different
        for k in range(4):
            mydict[probably_int(numbers.pop())] = probably_str(numbers.pop())
        correct += tc.map_of(int, str, checkonly=2)(mydict)
    assert correct > 0 and correct < 20  # should fail once about every 500000 runs


def test_range_int():
    @tc.typecheck
    def foo(x: tc.range(1, 11)) -> tc.range(1, 21):
        return 2 * x

    assert foo(1) == 2
    wrong_value = tc.InputParameterError("foo() has got an incompatible value for x: ")
    with expected(wrong_value):
        foo(2.0)
    with expected(wrong_value):
        foo(0)
    with expected(wrong_value):
        foo(20)
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: ")):
        foo(11)


def test_range_float():
    @tc.typecheck
    def foo(x: tc.range(1.0, 11.0)) -> tc.range(1.0, 21.0):
        return 2 * x

    assert foo(1.0) == 2.0
    wrong_value = tc.InputParameterError("foo() has got an incompatible value for x: ")
    with expected(wrong_value):
        foo(2)
    with expected(wrong_value):
        foo(0.0)
    with expected(wrong_value):
        foo(20.0)
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: ")):
        foo(11.0)


def test_range_str():
    @tc.typecheck
    def foo(x: tc.range("a", "b")):
        return x

    assert foo("abcdefg") == "abcdefg"
    wrong_value = tc.InputParameterError("foo() has got an incompatible value for x: ")
    with expected(wrong_value):
        foo("cdefg")
    with expected(wrong_value):
        foo("0")
    with expected(wrong_value):
        foo(64)


def test_range_wrong():
    with expected(AssertionError):
        @tc.typecheck
        def foo_highlow(x: tc.range(11, 1)): pass
    with expected(AssertionError):
        @tc.typecheck
        def foo_typemix(x: tc.range(1, 11.0)): pass

    class Unordered:
        def __init__(self):
            pass

    with expected(TypeError):
        @tc.typecheck
        def foo_unorderedtypes(x: tc.range(Unordered(), Unordered())): pass


def test_enum1():
    @tc.typecheck
    def foo(x: tc.enum(int, 1)) -> tc.enum(1, int):
        return x

    assert foo(1) == 1
    assert foo(int) is int
    with expected(tc.InputParameterError("foo() has got an incompatible value for x: 2")):
        foo(2)


def test_enum2():
    @tc.typecheck
    def bar(*, x: tc.enum(None)) -> tc.enum():
        return x

    with expected(tc.ReturnValueError("bar() has returned an incompatible value: None")):
        bar(x=None)


def test_enum3():
    with expected(tc.TypeCheckSpecificationError("the default value for x is incompatible with its typecheck")):
        @tc.typecheck
        def foo(x: tc.enum(1)=2):
            pass


def test_enum4():
    @tc.typecheck
    def foo(x: tc.optional(tc.enum(1, 2))=2):
        return x

    assert foo() == 2


def test_enum5():
    pred = tc.enum(1, 2.0, "three", [1] * 4)
    assert pred(2 * 1.0)
    assert pred("thr" + 2 * "e")
    assert pred([1, 1, 1, 1])
    assert pred(1.0)
    assert not pred("thr")
    assert not pred([1, 1])


def test_any1():
    @tc.typecheck
    def foo(x: tc.any()):
        pass

    with expected(tc.InputParameterError("foo() has got an incompatible value for x: 1")):
        foo(1)

    @tc.typecheck
    def bar(x: tc.any((int, float), tc.re("^foo$"), tc.enum(b"X", b"Y"))):
        pass

    bar((1, 1.0))
    bar("foo")
    bar(b"X")
    bar(b"Y")
    with expected(tc.InputParameterError("bar() has got an incompatible value for x: (1.0, 1)")):
        bar((1.0, 1))
    with expected(tc.InputParameterError("bar() has got an incompatible value for x: b'foo'")):
        bar(b"foo")
    with expected(tc.InputParameterError("bar() has got an incompatible value for x: X")):
        bar("X")
    with expected(tc.InputParameterError("bar() has got an incompatible value for x: Y")):
        bar("Y")


def test_any2():
    nothing_at_all = ((type(None),) * 1000)
    either_nothing = tc.any(tc.any(tc.any(tc.any(*nothing_at_all), *nothing_at_all), *nothing_at_all), *nothing_at_all)

    @tc.typecheck
    def biz(x) -> either_nothing:
        return x

    with expected(tc.ReturnValueError("biz() has returned an incompatible value: anything")):
        biz("anything")


def test_any3():
    @tc.typecheck
    def accept_number(x: tc.any(int, tc.re("^[0-9]+$"))):
        return int(x) + 1

    assert accept_number(1) == 2
    assert accept_number("1") == 2
    assert accept_number(-1) == 0
    with expected(tc.InputParameterError("accept_number() has got an incompatible value for x: -1")):
        accept_number("-1")


def test_all1():
    @tc.typecheck
    def foo(x: tc.all()):
        pass

    foo(foo)  # an empty all() accepts anything

    @tc.typecheck
    def bar(x: tc.all(tc.re("abcdef"), tc.re("defghi"), tc.re("^abc"))):
        pass

    bar("abcdefghijklm")
    with expected(tc.InputParameterError("bar() has got an incompatible value for x:  abcdefghi")):
        bar(" abcdefghi")
    with expected(tc.InputParameterError("bar() has got an incompatible value for x: abc defghi")):
        bar("abc defghi")


def test_all2():
    def complete_blocks(arg):
        return len(arg) % 512 == 0

    @tc.typecheck
    def foo_all(arg: tc.all(tc.any(bytes, bytearray), complete_blocks)): pass

    foo_all(b"x" * 512)  # OK
    foo_all(bytearray(b"x" * 1024))  # OK
    with expected(tc.InputParameterError("foo_all() has got an incompatible value for arg: xxx")):
        foo_all("x" * 512)  # Wrong: not a bytearray or bytes
    with expected(tc.InputParameterError("foo_all() has got an incompatible value for arg: b'xxx")):
        foo_all(b"x" * 1012)  # Wrong: no complete blocks


def test_none1():
    @tc.typecheck
    def foo(x: tc.none()):
        pass

    foo(foo)  # an empty none() accepts anything

    @tc.typecheck
    def taboo(x: tc.none(tc.re("foo"), tc.re("bar"))):
        pass

    taboo("boofar")
    with expected(tc.InputParameterError("taboo() has got an incompatible value for x: foofar")):
        taboo("foofar")
    with expected(tc.InputParameterError("taboo() has got an incompatible value for x: boobar-ism")):
        taboo("boobar-ism")


def test_none2():
    class TestCase:
        pass

    class MyCheckers(TestCase):
        pass

    class AddressTest:
        pass

    def classname_contains_Test(arg):
        return type(arg).__name__.find("Test") >= 0

    @tc.typecheck
    def no_tests_please(arg: tc.none(TestCase, classname_contains_Test)): pass

    no_tests_please("stuff")  # OK
    with expected(tc.InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(TestCase())  # Wrong: not wanted here
    with expected(tc.InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(MyCheckers())  # Wrong: superclass not wanted here
    with expected(tc.InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(AddressTest())  # Wrong: suspicious class name
