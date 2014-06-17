# To test typecheck-decorator, simply execute this file. No test framework is used.

# Most of this file is from the lower part of Dmitry Dvoinikov's
# http://www.targeted.org/python/recipes/typecheck3000.py
# reworked into py.test tests

import functools
import platform
import re
from random import randint, shuffle
from time import time
from traceback import extract_stack

from typecheck import typecheck  # TODO: @typecheck --> @tc.typecheck
import typecheck as tc
from typecheck import InputParameterError, ReturnValueError, TypeCheckSpecificationError

############################################################################

print("self-testing module typecheck on {} {}:".format(
    platform.python_implementation(), platform.python_version()))
print(str(platform.uname()))

############################################################################

class expected:
    def __init__(self, e, msg_regexp=None):
        if isinstance(e, Exception):
            self._type, self._msg = e.__class__, str(e)
        elif isinstance(e, type) and issubclass(e, Exception):
            self._type, self._msg = e, msg_regexp
        else:
            raise Exception("usage: 'with expected(Exception)'")

    def __enter__(self):  # make this a context handler
        try:
            pass
        except:
            pass # this is a Python3 way of saying sys.exc_clear()

    def __exit__(self, exc_type, exc_value, traceback):
        assert exc_type is not None, \
            "expected {0:s} to have been thrown".format(self._type.__name__)
        msg = str(exc_value)
        return (issubclass(exc_type, self._type) and
                (self._msg is None or
                 msg.startswith(self._msg) or  # for instance
                 re.match(self._msg, msg)))    # for class + regexp

############################################################################


def test_wrapped_function_keeps_its_name():
    @typecheck
    def foo() -> type(None):
        pass
    print("method proxy naming")
    assert foo.__name__ == "foo"


def test_no_excessive_proxying():
    @typecheck
    def foo():
        assert extract_stack()[-2][2] != "typecheck_invocation_proxy"
    foo()
    @typecheck
    def bar() -> type(None):
        assert extract_stack()[-2][2] == "typecheck_invocation_proxy"
    bar()


def test_double_annotations_wrapping():
    @typecheck
    def foo(x: int):
        return x
    assert foo(1) == typecheck(foo)(1) == 1


def test_empty_string_in_incompatible_values():
    @typecheck
    def foo(s: lambda s: s != "" = None):
        return s
    assert foo() is None
    assert foo(None) is None
    assert foo(0) == 0
    with expected(InputParameterError("foo() has got an incompatible value for s: ''")):
        foo("")
    @typecheck
    def foo(*, k: tc.optional(lambda s: s != "") = None):
        return k
    assert foo() is None
    assert foo(k = None) is None
    assert foo(k = 0) == 0
    with expected(InputParameterError("foo() has got an incompatible value for k: ''")):
        foo(k = "")
    @typecheck
    def foo(s = None) -> lambda s: s != "":
        return s
    assert foo() is None
    assert foo(None) is None
    assert foo(0) == 0
    with expected(ReturnValueError("foo() has returned an incompatible value: ''")):
        foo("")


def test_invalid_type_specification():
    with expected(TypeCheckSpecificationError("invalid typecheck for a")):
        @typecheck
        def foo(a: 10):
            pass
    with expected(TypeCheckSpecificationError("invalid typecheck for k")):
        @typecheck
        def foo(*, k: 10):
            pass
    with expected(TypeCheckSpecificationError("invalid typecheck for return")):
        @typecheck
        def foo() -> 10:
            pass


def test_incompatible_default_value():
    with expected(TypeCheckSpecificationError("the default value for b is incompatible with its typecheck")):
        @typecheck
        def ax_b2(a, b: int = "two"):
            pass
    with expected(TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @typecheck
        def a1_b2(a: int = "one", b = "two"):
            pass
    with expected(TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @typecheck
        def foo(a: str = None):
            pass
    with expected(TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @typecheck
        def kw(*, a: int = 1.0):
            pass
    with expected(TypeCheckSpecificationError("the default value for b is incompatible with its typecheck")):
        @typecheck
        def kw(*, a: int = 1, b: str = 10):
            pass


def test_can_change_default_value():
    @typecheck
    def foo(a: list = []):
        a.append(len(a))
        return a
    assert foo() == [0]
    assert foo() == [0, 1]
    assert foo([]) == [0]
    assert foo() == [0, 1, 2]
    assert foo() == [0, 1, 2, 3]
    @typecheck
    def foo(*, k: tc.optional(list) = []):
        k.append(len(k))
        return k
    assert foo() == [0]
    assert foo() == [0, 1]
    assert foo(k = []) == [0]
    assert foo() == [0, 1, 2]
    assert foo() == [0, 1, 2, 3]


def test_unchecked_args():
    @typecheck
    def axn_bxn(a, b):
        return a + b
    assert axn_bxn(10, 20) == 30
    assert axn_bxn(10, 20.0) == 30.0
    assert axn_bxn(10.0, 20) == 30.0
    assert axn_bxn(10.0, 20.0) == 30.0
    with expected(TypeError, "(?:axn_bxn\(\) takes exactly 2 (?:positional )?arguments \(1 given\)|"
                                "axn_bxn\(\) missing 1 required positional argument: 'b')"):
        axn_bxn(10)
    with expected(TypeError, "(?:axn_bxn\(\) takes exactly 2 (?:positional )?arguments \(0 given\)|"
                                "axn_bxn\(\) missing 2 required positional arguments: 'a' and 'b')"):
        axn_bxn()


def test_default_unchecked_args1():
    @typecheck
    def axn_b2n(a, b = 2):
        return a + b
    assert axn_b2n(10, 20) == 30
    assert axn_b2n(10, 20.0) == 30.0
    assert axn_b2n(10.0, 20) == 30.0
    assert axn_b2n(10.0, 20.0) == 30.0
    assert axn_b2n(10) == 12
    assert axn_b2n(10.0) == 12.0
    with expected(TypeError, "(?:axn_b2n\(\) takes at least 1 (?:positional )?argument \(0 given\)|"
                                "axn_b2n\(\) missing 1 required positional argument: 'a')"):
        axn_b2n()


def test_default_unchecked_args2():
    @typecheck
    def a1n_b2n(a = 1, b = 2):
        return a + b
    assert a1n_b2n(10, 20) == 30
    assert a1n_b2n(10, 20.0) == 30.0
    assert a1n_b2n(10.0, 20) == 30.0
    assert a1n_b2n(10.0, 20.0) == 30.0
    assert a1n_b2n(10) == 12
    assert a1n_b2n(10.0) == 12.0
    assert a1n_b2n() == 3


def test_simple_checked_args1():
    @typecheck
    def axc_bxn(a: int, b):
        return a + b
    assert axc_bxn(10, 20) == 30
    assert axc_bxn(10, 20.0) == 30.0
    with expected(InputParameterError("axc_bxn() has got an incompatible value for a: 10.0")):
        axc_bxn(10.0, 20)
    with expected(InputParameterError("axc_bxn() has got an incompatible value for a: 10.0")):
        axc_bxn(10.0, 20.0)
    with expected(TypeError, "(?:axc_bxn\(\) takes exactly 2 (?:positional )?arguments \(1 given\)|"
                                "axc_bxn\(\) missing 1 required positional argument: 'b')"):
        axc_bxn(10)
    with expected(TypeError, "(?:axc_bxn\(\) takes exactly 2 (?:positional )?arguments \(0 given\)|"
                                "axc_bxn\(\) missing 2 required positional arguments: 'a' and 'b')"):
        axc_bxn()


def test_simple_checked_args2():
    @typecheck
    def axn_bxc(a, b: int):
        return a + b
    assert axn_bxc(10, 20) == 30
    with expected(InputParameterError("axn_bxc() has got an incompatible value for b: 20.0")):
        axn_bxc(10, 20.0)
    assert axn_bxc(10.0, 20) == 30.0
    with expected(InputParameterError("axn_bxc() has got an incompatible value for b: 20.0")):
        axn_bxc(10.0, 20.0)
    with expected(TypeError, "(?:axn_bxc\(\) takes exactly 2 (?:positional )?arguments \(1 given\)|"
                                "axn_bxc\(\) missing 1 required positional argument: 'b')"):
        axn_bxc(10)
    with expected(TypeError, "(?:axn_bxc\(\) takes exactly 2 (?:positional )?arguments \(0 given\)|"
                                "axn_bxc\(\) missing 2 required positional arguments: 'a' and 'b')"):
        axn_bxc()


def test_simple_default_checked_args1():
    @typecheck
    def axn_b2c(a, b: int = 2):
        return a + b
    assert axn_b2c(10, 20) == 30
    with expected(InputParameterError("axn_b2c() has got an incompatible value for b: 20.0")):
        axn_b2c(10, 20.0)
    assert axn_b2c(10.0, 20) == 30.0
    with expected(InputParameterError("axn_b2c() has got an incompatible value for b: 20.0")):
        axn_b2c(10.0, 20.0)
    assert axn_b2c(10) == 12
    assert axn_b2c(10.0) == 12.0
    with expected(TypeError, "(?:axn_b2c\(\) takes at least 1 (?:positional )?argument \(0 given\)|"
                                "axn_b2c\(\) missing 1 required positional argument: 'a')"):
        axn_b2c()


def test_simple_default_checked_args2():
    @typecheck
    def a1n_b2c(a = 1, b: int = 2):
        return a + b
    assert a1n_b2c(10, 20) == 30
    with expected(InputParameterError("a1n_b2c() has got an incompatible value for b: 20.0")):
        a1n_b2c(10, 20.0)
    assert a1n_b2c(10.0, 20) == 30.0
    with expected(InputParameterError("a1n_b2c() has got an incompatible value for b: 20.0")):
        a1n_b2c(10.0, 20.0)
    assert a1n_b2c(10) == 12
    assert a1n_b2c(10.0) == 12.0
    assert a1n_b2c() == 3


def test_simple_default_checked_args3():
    @typecheck
    def axc_b2n(a: int, b = 2):
        return a + b
    assert axc_b2n(10, 20) == 30
    assert axc_b2n(10, 20.0) == 30.0
    with expected(InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0, 20)
    with expected(InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0, 20.0)
    assert axc_b2n(10) == 12
    with expected(InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0)
    with expected(TypeError, "(?:axc_b2n\(\) takes at least 1 (?:positional )?argument \(0 given\)|"
                                "axc_b2n\(\) missing 1 required positional argument: 'a')"):
        axc_b2n()


def test_simple_default_checked_args4():
    @typecheck
    def a1c_b2n(a: int = 1, b = 2):
        return a + b
    assert a1c_b2n(10, 20) == 30
    assert a1c_b2n(10, 20.0) == 30.0
    with expected(InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0, 20)
    with expected(InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0, 20.0)
    assert a1c_b2n(10) == 12
    with expected(InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0)
    assert a1c_b2n() == 3


def test_simple_checked_args3():
    @typecheck
    def axc_bxc(a: int, b: int):
        return a + b
    assert axc_bxc(10, 20) == 30
    with expected(InputParameterError("axc_bxc() has got an incompatible value for b: 20.0")):
        axc_bxc(10, 20.0)
    with expected(InputParameterError("axc_bxc() has got an incompatible value for a: 10.0")):
        axc_bxc(10.0, 20)
    with expected(InputParameterError("axc_bxc() has got an incompatible value for a: 10.0")):
        axc_bxc(10.0, 20.0)
    with expected(TypeError, "(?:axc_bxc\(\) takes exactly 2 (?:positional )?arguments \(1 given\)|"
                                "axc_bxc\(\) missing 1 required positional argument: 'b')"):
        axc_bxc(10)
    with expected(TypeError, "(?:axc_bxc\(\) takes exactly 2 (?:positional )?arguments \(0 given\)|"
                                "axc_bxc\(\) missing 2 required positional arguments: 'a' and 'b')"):
        axc_bxc()


def test_simple_default_checked_args5():
    @typecheck
    def axc_b2c(a: int, b: int = 2):
        return a + b
    assert axc_b2c(10, 20) == 30
    with expected(InputParameterError("axc_b2c() has got an incompatible value for b: 20.0")):
        axc_b2c(10, 20.0)
    with expected(InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0, 20)
    with expected(InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0, 20.0)
    assert axc_b2c(10) == 12
    with expected(InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0)
    with expected(TypeError, "(?:axc_b2c\(\) takes at least 1 (?:positional )?argument \(0 given\)|"
                                "axc_b2c\(\) missing 1 required positional argument: 'a')"):
        axc_b2c()


def test_simple_default_checked_args6():
    @typecheck
    def a1c_b2c(a: int = 1, b: int = 2):
        return a + b
    assert a1c_b2c(10, 20) == 30
    with expected(InputParameterError("a1c_b2c() has got an incompatible value for b: 20.0")):
        a1c_b2c(10, 20.0)
    with expected(InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0, 20)
    with expected(InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0, 20.0)
    assert a1c_b2c(10) == 12
    with expected(InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0)
    assert a1c_b2c() == 3


############################################################################

def test_default_vs_checked_args_random_generated():
    test_passes = 0
    start = time()
    while time() < start + 1.0:
        N = randint(1, 10)
        DN = randint(0, N)
        args = [ "a{0:03d}".format(i) for i in range(N) ]
        chkd = [ randint(0, 1) for i in range(N) ]
        deft = [ i >= DN for i in range(N) ]
        def_args = ", ".join(map(lambda x: "{0}{1}{2}".format(x[1][0], x[1][1] and ": int" or "",
                                                              x[1][2] and " = {0}".format(x[0]) or ""),
                                 enumerate(zip(args, chkd, deft))))
        sum_args = " + ".join(args)
        test = "@typecheck\n" \
               "def some_func({def_args}):\n" \
               "    return {sum_args}\n"
        for provided_args in range(DN, N + 1):
            success_args = [j * 10 for j in range(provided_args)]
            success_result = provided_args * (provided_args - 1) * 9 // 2 + N * (N - 1) // 2
            test_run = test
            test_run += "assert some_func({success_args}) == {success_result}\n"
            failure_args = [ j for (j, c) in enumerate(chkd) if j < provided_args and c ]
            if failure_args:
                shuffle(failure_args)
                failure_arg = failure_args[0]
                failure_value = failure_arg * 10.0
                failure_args = success_args[:]
                failure_args[failure_arg] = failure_value
                test_run += "with expected(InputParameterError('some_func() has got an " \
                                           "incompatible value for a{failure_arg:03d}: {failure_value}')):\n" \
                            "    some_func({failure_args})\n"
                failure_args = ", ".join(map(str, failure_args))

            success_args = ", ".join(map(str, success_args))
            exec(test_run.format(**locals()))
            test_passes += 1
    print("{0} tests passed ok".format(test_passes))

############################################################################

def test_default_vs_checked_kwargs1():
    @typecheck
    def foo(*, a: str):
        return a
    with expected(InputParameterError("foo() has got an incompatible value for a: <no value>")):
        foo()
    assert foo(a = "b") == "b"


def test_default_vs_checked_kwargs2():
    @typecheck
    def foo(*, a: tc.optional(str) = "a"):
        return a
    assert foo() == "a"
    assert foo(a = "b") == "b"
    with expected(InputParameterError("foo() has got an incompatible value for a: 10")):
        foo(a = 10)


def test_default_vs_checked_kwargs3():
    @typecheck
    def pxn_qxn(*, p, q, **kwargs):
        return p + q
    assert pxn_qxn(p = 1, q = 2) == 3
    assert pxn_qxn(p = 1, q = 2.0) == 3.0
    assert pxn_qxn(p = 1.0, q = 2) == 3.0
    assert pxn_qxn(p = 1.0, q = 2.0) == 3.0
    with expected(TypeError, "(?:pxn_qxn\(\) needs keyword-only argument q|"
                                "pxn_qxn\(\) missing 1 required keyword-only argument: 'q')"):
        pxn_qxn(p = 1)
    with expected(TypeError, "(?:pxn_qxn\(\) needs keyword-only argument p|"
                                "pxn_qxn\(\) missing 1 required keyword-only argument: 'p')"):
        pxn_qxn(q = 2)
    with expected(TypeError, "(?:pxn_qxn\(\) needs keyword-only argument p|"
                                "pxn_qxn\(\) missing 2 required keyword-only arguments: 'p' and 'q')"):
        pxn_qxn()


def test_default_vs_checked_kwargs4():
    @typecheck
    def pxn_q2n(*, p, q = 2):
        return p + q
    assert pxn_q2n(p = 1, q = 2) == 3
    assert pxn_q2n(p = 1, q = 2.0) == 3.0
    assert pxn_q2n(p = 1.0, q = 2) == 3.0
    assert pxn_q2n(p = 1.0, q = 2.0) == 3.0
    assert pxn_q2n(p = 1) == 3
    with expected(TypeError, "(?:pxn_q2n\(\) needs keyword-only argument p|"
                                "pxn_q2n\(\) missing 1 required keyword-only argument: 'p')"):
        pxn_q2n(q = 2)
    with expected(TypeError, "(?:pxn_q2n\(\) needs keyword-only argument p|"
                                "pxn_q2n\(\) missing 1 required keyword-only argument: 'p')"):
        pxn_q2n()


def test_default_vs_checked_kwargs5():
    @typecheck
    def p1n_q2n(*, p = 1, q = 2):
        return p + q
    assert p1n_q2n(p = 1, q = 2) == 3
    assert p1n_q2n(p = 1, q = 2.0) == 3.0
    assert p1n_q2n(p = 1.0, q = 2) == 3.0
    assert p1n_q2n(p = 1.0, q = 2.0) == 3.0
    assert p1n_q2n(p = 1) == 3
    assert p1n_q2n(q = 2) == 3
    assert p1n_q2n() == 3


def test_default_vs_checked_kwargs6():
    @typecheck
    def pxn_qxc(*, p, q: int):
        return p + q
    assert pxn_qxc(p = 1, q = 2) == 3
    with expected(InputParameterError("pxn_qxc() has got an incompatible value for q: 2.0")):
        pxn_qxc(p = 1, q = 2.0)
    assert pxn_qxc(p = 1.0, q = 2) == 3.0
    with expected(InputParameterError("pxn_qxc() has got an incompatible value for q: 2.0")):
        pxn_qxc(p = 1.0, q = 2.0)
    with expected(InputParameterError("pxn_qxc() has got an incompatible value for q: <no value>")):
        pxn_qxc(p = 1)
    with expected(TypeError, "(?:pxn_qxc\(\) needs keyword-only argument p|"
                                "pxn_qxc\(\) missing 1 required keyword-only argument: 'p')"):
        pxn_qxc(q = 2)
    with expected(InputParameterError("pxn_qxc() has got an incompatible value for q: <no value>")):
        pxn_qxc()


def test_default_vs_checked_kwargs7():
    @typecheck
    def pxn_q2c(*, p, q: int = 2):
        return p + q
    assert pxn_q2c(p = 1, q = 2) == 3
    with expected(InputParameterError("pxn_q2c() has got an incompatible value for q: 2.0")):
        pxn_q2c(p = 1, q = 2.0)
    assert pxn_q2c(p = 1.0, q = 2) == 3.0
    with expected(InputParameterError("pxn_q2c() has got an incompatible value for q: 2.0")):
        pxn_q2c(p = 1.0, q = 2.0)
    with expected(InputParameterError("pxn_q2c() has got an incompatible value for q: <no value>")):
        pxn_q2c(p = 1)
    with expected(TypeError, "(?:pxn_q2c\(\) needs keyword-only argument p|"
                                "pxn_q2c\(\) missing 1 required keyword-only argument: 'p')"):
        pxn_q2c(q = 2)
    with expected(InputParameterError("pxn_q2c() has got an incompatible value for q: <no value>")):
        pxn_q2c()


def test_default_vs_checked_kwargs8():
    @typecheck
    def p1n_q2c(*, p = 1, q: int = 2):
        return p + q
    assert p1n_q2c(p = 1, q = 2) == 3
    with expected(InputParameterError("p1n_q2c() has got an incompatible value for q: 2.0")):
        p1n_q2c(p = 1, q = 2.0)
    assert p1n_q2c(p = 1.0, q = 2) == 3.0
    with expected(InputParameterError("p1n_q2c() has got an incompatible value for q: 2.0")):
        p1n_q2c(p = 1.0, q = 2.0)
    with expected(InputParameterError("p1n_q2c() has got an incompatible value for q: <no value>")):
        p1n_q2c(p = 1)
    assert p1n_q2c(q = 2) == 3
    with expected(InputParameterError("p1n_q2c() has got an incompatible value for q: <no value>")):
        p1n_q2c()


def test_default_vs_checked_kwargs9():
    @typecheck
    def pxc_qxc(*, p: int, q: int):
        return p + q
    assert pxc_qxc(p = 1, q = 2) == 3
    with expected(InputParameterError("pxc_qxc() has got an incompatible value for q: 2.0")):
        pxc_qxc(p = 1, q = 2.0)
    with expected(InputParameterError("pxc_qxc() has got an incompatible value for p: 1.0")):
        pxc_qxc(p = 1.0, q = 2)
    with expected(InputParameterError,
                  "pxc_qxc\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        pxc_qxc(p = 1.0, q = 2.0)
    with expected(InputParameterError("pxc_qxc() has got an incompatible value for q: <no value>")):
        pxc_qxc(p = 1)
    with expected(InputParameterError("pxc_qxc() has got an incompatible value for p: <no value>")):
        pxc_qxc(q = 2)
    with expected(InputParameterError,
                  "pxc_qxc\(\) has got an incompatible value for [pq]: <no value>"):
        pxc_qxc()


def test_default_vs_checked_kwargs10():
    @typecheck
    def pxc_q2c(*, p: int, q: int = 2):
        return p + q
    assert pxc_q2c(p = 1, q = 2) == 3
    with expected(InputParameterError("pxc_q2c() has got an incompatible value for q: 2.0")):
        pxc_q2c(p = 1, q = 2.0)
    with expected(InputParameterError("pxc_q2c() has got an incompatible value for p: 1.0")):
        pxc_q2c(p = 1.0, q = 2)
    with expected(InputParameterError,
                  "pxc_q2c\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        pxc_q2c(p = 1.0, q = 2.0)
    #TODO: should tc.optional() be required when a default is given? No! (also elsewhere)
    with expected(InputParameterError("pxc_q2c() has got an incompatible value for q: <no value>")):
        pxc_q2c(p = 1)
    with expected(InputParameterError("pxc_q2c() has got an incompatible value for p: <no value>")):
        pxc_q2c(q = 2)


def test_default_vs_checked_kwargs11():
    @typecheck
    def p1c_q2c(*, p: int = 1, q: int = 2):
        return p + q
    assert p1c_q2c(p = 1, q = 2) == 3
    with expected(InputParameterError("p1c_q2c() has got an incompatible value for q: 2.0")):
        p1c_q2c(p = 1, q = 2.0)
    with expected(InputParameterError("p1c_q2c() has got an incompatible value for p: 1.0")):
        p1c_q2c(p = 1.0, q = 2)
    with expected(InputParameterError,
                  "p1c_q2c\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        p1c_q2c(p = 1.0, q = 2.0)
    with expected(InputParameterError("p1c_q2c() has got an incompatible value for q: <no value>")):
        p1c_q2c(p = 1)
    with expected(InputParameterError("p1c_q2c() has got an incompatible value for p: <no value>")):
        p1c_q2c(q = 2)


def test_default_vs_checked_kwargs_randomly_generated():
    test_passes = 0
    start = time()
    while time() < start + 1.0:
        N = randint(1, 10)
        kwrs = [ "k{0:03d}".format(i) for i in range(N) ]
        chkd = [ randint(0, 1) for i in range(N) ]
        deft = [ randint(0, 1) for i in range(N) ]
        def_kwrs = ", ".join("{0}{1}{2}".format(k, c and ": tc.optional(int)" or "", d and " = {0}".format(i) or "")
                             for (i, (k, c, d)) in enumerate(zip(kwrs, chkd, deft)))
        sum_kwrs = " + ".join(kwrs)
        test = "@typecheck\n" \
               "def some_func(*, {def_kwrs}):\n" \
               "    return {sum_kwrs}\n"
        for i in range(N):
            success_kwrs = { k: i * 10 for (i, (k, c, d)) in enumerate(zip(kwrs, chkd, deft))
                                       if (not d) or randint(0, 1) }
            temp_kwrs = success_kwrs.copy()
            temp_kwrs.update({ k: i for (i, (k, d)) in enumerate(zip(kwrs, deft))
                                    if d and k not in success_kwrs })
            success_result = sum(temp_kwrs.values())
            test_run = test
            test_run += "kwargs = {success_kwrs}\n" \
                        "assert some_func(**kwargs) == {success_result}\n"
            failure_kwrs = success_kwrs.copy()
            for k, v in failure_kwrs.items():
                if chkd[int(k[1:])] and randint(0, 1):
                    failure_kwarg = k
                    failure_value = float(v)
                    failure_kwrs[failure_kwarg] = failure_value
                    test_run += "kwargs = {failure_kwrs}\n" \
                                "with expected(InputParameterError('some_func() has got an " \
                                               "incompatible value for {failure_kwarg}: {failure_value}')):\n" \
                                "    some_func(**kwargs)\n"
                    break
            exec(test_run.format(**locals()))
            test_passes += 1


def test_TypeChecker():
    @typecheck
    def foo(a: int) -> object:
        return a
    assert foo(10) == 10
    @typecheck
    def foo(*args, a: str) -> float:
        return float(a)
    assert foo(a = "10.0") == 10.0
    class Foo():
        pass
    class Bar(Foo):
        pass
    @typecheck
    def foo(a: Bar) -> Foo:
        return a
    f = Bar()
    assert foo(f) is f
    f = Foo()
    with expected(InputParameterError("foo() has got an incompatible value for a: <")):
        foo(f)
    @typecheck
    def foo(a: Foo) -> Bar:
        return a
    f = Bar()
    assert foo(f) is f
    f = Foo()
    with expected(ReturnValueError("foo() has returned an incompatible value: <")):
        foo(f)


############################################################################

def test_FixedSequenceChecker1():
    @typecheck
    def foo(a: (int,str) = (1,"!"), *, k: tc.optional(()) = ()) -> (str, ()):
        return a[1], k
    assert foo() == ("!", ())
    assert foo((2,"x")) == ("x", ())
    assert foo(k = ()) == ("!", ())
    assert foo((33,"44"), k = ()) == ("44", ())
    assert foo([3,"4"]) == ("4", ())
    assert foo(k = []) == ("!", [])
    with expected(InputParameterError("foo() has got an incompatible value for a: (1,)")):
        foo((1, ))
    with expected(InputParameterError("foo() has got an incompatible value for k: (1, 2)")):
        foo(k = (1, 2))


def test_FixedSequenceChecker2():
    @typecheck
    def foo(a: [] = [], *, k: tc.optional([]) = None) -> ([], tc.optional([])):
        return a, k
    assert foo() == ([], None)
    assert foo([]) == ([], None)
    assert foo(k = []) == ([], [])
    assert foo([], k = []) == ([], [])
    with expected(InputParameterError("foo() has got an incompatible value for a: ()")):
        foo(())
    with expected(InputParameterError("foo() has got an incompatible value for a: (1,)")):
        foo((1, ))
    with expected(InputParameterError("foo() has got an incompatible value for k: ()")):
        foo(k = ())
    with expected(InputParameterError("foo() has got an incompatible value for k: (1,)")):
        foo(k = (1, ))


def test_FixedSequenceChecker3():
    @typecheck
    def foo(*args) -> (int, str):
        return args
    foo(1, "2") == 1, "2"
    with expected(ReturnValueError("foo() has returned an incompatible value: (1, 2)")):
        foo(1, 2)
    with expected(ReturnValueError("foo() has returned an incompatible value: (1, '2', None)")):
        foo(1, "2", None)
    with expected(ReturnValueError("foo() has returned an incompatible value: (1,)")):
        foo(1)


def test_FixedSequenceChecker4():
    @typecheck
    def foo(*, k: tc.optional([[[[lambda x: x % 3 == 1]]]]) = [[[[4]]]]):
        return k[0][0][0][0]
    assert foo() % 3 == 1
    assert foo(k = [[[[1]]]]) % 3 == 1
    with expected(InputParameterError("foo() has got an incompatible value for k: [[[[5]]]]")):
        foo(k = [[[[5]]]])


def test_CallableChecker1():
    @typecheck
    def foo(a: callable, *, k: callable) -> callable:
        return a(k(lambda: 2))
    x = lambda x: x
    assert foo(x, k = x)() == 2


def test_CallableChecker2():
    class NumberToolset:
        @classmethod
        @typecheck
        def is_even(cls, value: int) -> bool:
            return value % 2 == 0
        @staticmethod
        @typecheck
        def is_odd(value: int) -> bool:
            return not NumberToolset.is_even(value)
    @typecheck
    def foo(a: NumberToolset.is_even = 0) -> NumberToolset.is_odd:
        return a + 1
    assert foo() == 1
    assert foo(2) == 3
    with expected(InputParameterError("is_even() has got an incompatible value for value: 1.0")):
        foo(1.0)


def test_CallableChecker3():
    @typecheck
    def foo(x = None) -> type(None):
        return x
    assert foo() is None
    with expected(ReturnValueError("foo() has returned an incompatible value: ''")):
        foo("")


def test_OptionalChecker1():
    @typecheck
    def foo(b: bool) -> bool:
        return not b
    assert foo(True) is False
    assert foo(False) is True
    with expected(InputParameterError("foo() has got an incompatible value for b: 0")):
        foo(0)
    @typecheck
    def foo(*, b: tc.optional(bool) = None) -> bool:
        return b
    assert foo(b = False) is False
    with expected(ReturnValueError("foo() has returned an incompatible value: None")):
        foo()


def test_OptionalChecker2():
    not_none = lambda x: x is not None
    with expected(TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @typecheck
        def foo(a: not_none = None):
            return a
    @typecheck
    def foo(a: tc.optional(not_none) = None): # note how optional overrides the not_none
        return a
    assert foo() is None
    assert foo(None) is None
    with expected(TypeCheckSpecificationError("the default value for k is incompatible with its typecheck")):
        @typecheck
        def foo(*, k: not_none = None):
            return k
    @typecheck
    def foo(*, k: tc.optional(not_none) = None): # note how optional overrides the not_none
        return k
    assert foo() is None
    assert foo(k = None) is None
    @typecheck
    def foo(x = None) -> not_none:
        return x
    with expected(ReturnValueError("foo() has returned an incompatible value: None")):
        foo()
    @typecheck
    def foo(x = None) -> tc.optional(not_none): # note how optional overrides the not_none
        return x
    assert foo() is None
    assert foo(None) is None


def test_hasattrs1():
    class FakeIO:
        def write(self):
            pass
        def flush(self):
            pass
    @typecheck
    def foo(a: tc.hasattrs("write", "flush")):
        pass
    foo(FakeIO())
    del FakeIO.flush
    with expected(InputParameterError("foo() has got an incompatible value for a: <")):
        foo(FakeIO())


def test_hasattrs2():
    assert tc.hasattrs("__class__")(int) and tc.hasattrs("__class__").check(int)
    assert not tc.hasattrs("foo")(int) and not tc.hasattrs("foo").check(int)


def test_has1():
    assert tc.has("^abc$")("abc")
    assert not tc.has("^abc$")(b"abc")
    assert not tc.has(b"^abc$")("abc")
    assert tc.has(b"^abc$")(b"abc")
    assert tc.has(b"^foo\x00bar$")(b"foo\x00bar")
    assert not tc.has(b"^foo\x00bar$")(b"foo\x00baz")
    assert tc.has("^abc")("abc\n")
    assert tc.has(b"^abc")(b"abc\n")
    assert not tc.has("^abc$")("abc\n")
    assert not tc.has(b"^abc$")(b"abc\n")
    assert not tc.has("^abc$")("abcx")
    assert not tc.has(b"^abc$")(b"abcx")


def test_has2():
    @typecheck
    def foo(*, k: tc.has("^[0-9A-F]+$")) -> tc.has("^[0-9]+$"):
        return "".join(reversed(k))
    assert foo(k = "1234") == "4321"
    with expected(InputParameterError("foo() has got an incompatible value for k: ''")):
        foo(k = "")
    with expected(InputParameterError("foo() has got an incompatible value for k: 1")):
        foo(k = 1)
    with expected(ReturnValueError("foo() has returned an incompatible value: DAB")):
        foo(k = "BAD")


def test_has3():
    @typecheck
    def foo(*, k: (tc.has("^1$"), [tc.has("^x$"), tc.has("^y$")])):
        return k[0] + k[1][0] + k[1][1]
    assert foo(k = ("1", ["x", "y"])) == "1xy"
    with expected(InputParameterError("foo() has got an incompatible value for k: ('2', ['x', 'y'])")):
        foo(k = ("2", ["x", "y"]))
    with expected(InputParameterError("foo() has got an incompatible value for k: ('1', ['X', 'y'])")):
        foo(k = ("1", ["X", "y"]))
    with expected(InputParameterError("foo() has got an incompatible value for k: ('1', ['x', 'Y'])")):
        foo(k = ("1", ["x", "Y"]))


def test_has4():
    russian = "\u0410\u0411\u0412\u0413\u0414\u0415\u0401\u0416\u0417\u0418\u0419\u041a" \
              "\u041b\u041c\u041d\u041e\u041f\u0420\u0421\u0422\u0423\u0424\u0425\u0426" \
              "\u0427\u0428\u0429\u042c\u042b\u042a\u042d\u042e\u042f\u0430\u0431\u0432" \
              "\u0433\u0434\u0435\u0451\u0436\u0437\u0438\u0439\u043a\u043b\u043c\u043d" \
              "\u043e\u043f\u0440\u0441\u0442\u0443\u0444\u0445\u0446\u0447\u0448\u0449" \
              "\u044c\u044b\u044a\u044d\u044e\u044f"
    assert len(russian) == 66
    @typecheck
    def foo(s: tc.has("^[{0}]$".format(russian))):
        return len(s)
    for c in russian:
        assert foo(c) == 1
    with expected(InputParameterError("foo() has got an incompatible value for s: @")):
        foo("@")


def test_has5():
    @typecheck
    def numbers_only_please(s: tc.has("^[0-9]+$")):
        pass
    numbers_only_please("123")
    with expected(InputParameterError("numbers_only_please() has got an incompatible value for s: 123")):
        numbers_only_please("123\x00HUH?")


def test_has6():
    assert tc.has("^123$")("123") and tc.has("^123$").check("123")
    assert not tc.has("^123$")("foo") and not tc.has("^123$").check("foo")


def test_tuple_of1():
    @typecheck
    def foo(x: tc.tuple_of(int)) -> tc.tuple_of(float):
        return tuple(map(float, x))
    assert foo(()) == ()
    assert foo((1, 2, 3)) == (1.0, 2.0, 3.0)
    with expected(InputParameterError("foo() has got an incompatible value for x: ('1.0',)")):
        foo(("1.0",))
    with expected(InputParameterError("foo() has got an incompatible value for x: []")):
        foo([])


def test_tuple_of2():
    @typecheck
    def foo(x: tc.tuple_of([tc.has("^[01]+$"), int])) -> bool:
        return functools.reduce(lambda r, e: r and int(e[0], 2) == e[1],
                                x, True)
    assert foo((["1010", 10], ["0101", 5]))
    assert not foo((["1010", 10], ["0111", 77]))


def test_tuple_of3():
    assert tc.tuple_of(tc.optional(tc.has("^foo$")))(("foo", None, "foo")) and \
           tc.tuple_of(tc.optional(tc.has("^foo$"))).check(("foo", None, "foo"))
    assert not tc.tuple_of(tc.optional(tc.has("^foo$")))(("123", None, "foo")) and \
           not tc.tuple_of(tc.optional(tc.has("^foo$"))).check(("123", None, "foo"))


def test_list_of1():
    @typecheck
    def foo(x: tc.list_of(int)) -> tc.list_of(float):
        return list(map(float, x))
    assert foo([]) == []
    assert foo([1, 2, 3]) == [1.0, 2.0, 3.0]
    with expected(InputParameterError("foo() has got an incompatible value for x: ['1.0']")):
        foo(["1.0"])
    with expected(InputParameterError("foo() has got an incompatible value for x: ()")):
        foo(())


def test_list_of2():
    @typecheck
    def foo(x: tc.list_of((tc.has("^[01]+$"), int))) -> bool:
        return functools.reduce(lambda r, e: r and int(e[0], 2) == e[1],
                                x, True)
    assert foo([("1010", 10), ("0101", 5)])
    assert not foo([("1010", 10), ("0111", 77)])


def test_list_of3():
    assert tc.list_of(tc.optional(tc.has("^foo$")))(["foo", None, "foo"]) and \
           tc.list_of(tc.optional(tc.has("^foo$"))).check(["foo", None, "foo"])
    assert not tc.list_of(tc.optional(tc.has("^foo$")))(["123", None, "foo"]) and \
           not tc.list_of(tc.optional(tc.has("^foo$"))).check(["123", None, "foo"])


def test_sequence_of1():
    @typecheck
    def foo(x: tc.sequence_of(int)) -> tc.sequence_of(float):
        return list(map(float, x))
    assert foo([]) == []
    assert foo(()) == []
    assert foo([1, 2, 3]) == [1.0, 2.0, 3.0]
    with expected(InputParameterError("foo() has got an incompatible value for x: ['1.0']")):
        foo(["1.0"])


def test_sequence_of2():
    @typecheck
    def foo(x: tc.sequence_of((tc.has("^[01]+$"), int))) -> bool:
        return functools.reduce(lambda r, e: r and int(e[0], 2) == e[1],
                                x, True)
    assert foo([("1010", 10), ("0101", 5)])
    assert not foo([("1010", 10), ("0111", 77)])


def test_sequence_of3():
    assert tc.sequence_of(tc.optional(tc.has("^foo$")))(["foo", None, "foo"]) and \
           tc.sequence_of(tc.optional(tc.has("^foo$"))).check(["foo", None, "foo"])
    assert not tc.sequence_of(tc.optional(tc.has("^foo$")))(["123", None, "foo"]) and \
           not tc.sequence_of(tc.optional(tc.has("^foo$"))).check(["foo", None, "1234"])


def test_dict_of1():
    @typecheck
    def foo(x: tc.dict_of(int, str)) -> tc.dict_of(str, int):
        return { v: k for k, v in x.items() }
    assert foo({}) == {}
    assert foo({1: "1", 2: "2"}) == {"1": 1, "2": 2}
    with expected(InputParameterError("foo() has got an incompatible value for x: []")):
        foo([])
    with expected(InputParameterError("foo() has got an incompatible value for x: {'1': '2'}")):
        foo({"1": "2"})
    with expected(InputParameterError("foo() has got an incompatible value for x: {1: 2}")):
        foo({1: 2})


def test_dict_of2():
    @typecheck
    def foo(*, k: tc.dict_of((int, int), [tc.has("^[0-9]+$"), tc.has("^[0-9]+$")])):
        return functools.reduce(lambda r, t: r and str(t[0][0]) == t[1][0] and str(t[0][1]) == t[1][1],
                                k.items(), True)
    assert foo(k = { (1, 2): ["1", "2"], (3, 4): ["3", "4"]})
    assert not foo(k = { (1, 3): ["1", "2"], (3, 4): ["3", "4"]})
    assert not foo(k = { (1, 2): ["1", "2"], (3, 4): ["3", "5"]})
    with expected(InputParameterError("foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3, 4): ['3', 'x']}")):
        foo(k = { (1, 2): ["1", "2"], (3, 4): ["3", "x"]})
    with expected(InputParameterError("foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3,): ['3', '4']}")):
        foo(k = { (1, 2): ["1", "2"], (3, ): ["3", "4"]})
    with expected(InputParameterError("foo() has got an incompatible value for k: {(1, 2): ['1', '2'], (3, 4.0): ['3', '4']}")):
        foo(k = { (1, 2): ["1", "2"], (3, 4.0): ["3", "4"]})


def test_dict_of3():
    assert tc.dict_of(int, tc.optional(str))({ 1: "foo", 2: None }) and \
           tc.dict_of(int, tc.optional(str)).check({ 1: "foo", 2: None })
    assert not tc.dict_of(int, tc.optional(str))({ None: "foo", 2: None }) and \
           not tc.dict_of(int, tc.optional(str)).check({ None: "foo", 2: None })


def test_enum1():
    @typecheck
    def foo(x: tc.enum(int, 1)) -> tc.enum(1, int):
        return x
    assert foo(1) == 1
    assert foo(int) is int
    with expected(InputParameterError("foo() has got an incompatible value for x: 2")):
        foo(2)


def test_enum2():
    @typecheck
    def bar(*, x: tc.enum(None)) -> tc.enum():
        return x
    with expected(ReturnValueError("bar() has returned an incompatible value: None")):
        bar(x = None)


def test_enum3():
    with expected(TypeCheckSpecificationError("the default value for x is incompatible with its typecheck")):
        @typecheck
        def foo(x: tc.enum(1) = 2):
            pass


def test_enum4():
    @typecheck
    def foo(x: tc.optional(tc.enum(1, 2)) = 2):
        return x
    assert foo() == 2


def test_any1():
    @typecheck
    def foo(x: tc.any()):
        pass
    with expected(InputParameterError("foo() has got an incompatible value for x: 1")):
        foo(1)
    @typecheck
    def bar(x: tc.any((int, float), tc.has("^foo$"), tc.enum(b"X", b"Y"))):
        pass
    bar((1, 1.0))
    bar("foo")
    bar(b"X")
    bar(b"Y")
    with expected(InputParameterError("bar() has got an incompatible value for x: (1.0, 1)")):
        bar((1.0, 1))
    with expected(InputParameterError("bar() has got an incompatible value for x: b'foo'")):
        bar(b"foo")
    with expected(InputParameterError("bar() has got an incompatible value for x: X")):
        bar("X")
    with expected(InputParameterError("bar() has got an incompatible value for x: Y")):
        bar("Y")

def test_any2():
    nothing_at_all = ((type(None), ) * 1000)
    either_nothing = tc.any(tc.any(tc.any(tc.any(*nothing_at_all), *nothing_at_all), *nothing_at_all), *nothing_at_all)
    @typecheck
    def biz(x) -> either_nothing:
        return x
    with expected(ReturnValueError("biz() has returned an incompatible value: anything")):
        biz("anything")

def test_any3():
    @typecheck
    def accept_number(x: tc.any(int, tc.has("^[0-9]+$"))):
        return int(x) + 1
    assert accept_number(1) == 2
    assert accept_number("1") == 2
    assert accept_number(-1) == 0
    with expected(InputParameterError("accept_number() has got an incompatible value for x: -1")):
        accept_number("-1")


def test_all1():
    @typecheck
    def foo(x: tc.all()):
        pass
    foo(foo)   # an empty all() accepts anything
    @typecheck
    def bar(x: tc.all(tc.has("abcdef"), tc.has("defghi"), tc.has("^abc"))):
        pass
    bar("abcdefghijklm")
    with expected(InputParameterError("bar() has got an incompatible value for x:  abcdefghi")):
        bar(" abcdefghi")
    with expected(InputParameterError("bar() has got an incompatible value for x: abc defghi")):
        bar("abc defghi")

def test_all2():
    def complete_blocks(arg):
       return len(arg) % 512 == 0
    @typecheck
    def foo_all(arg: tc.all(tc.any(bytes,bytearray), complete_blocks)): pass
    foo_all(b"x" * 512)              # OK
    foo_all(bytearray(b"x" * 1024))  # OK
    with expected(InputParameterError("foo_all() has got an incompatible value for arg: xxx")):
        foo_all("x" * 512)      # Wrong: not a bytearray or bytes
    with expected(InputParameterError("foo_all() has got an incompatible value for arg: b'xxx")):
        foo_all(b"x" * 1012)    # Wrong: no complete blocks


def test_none1():
    @typecheck
    def foo(x: tc.none()):
        pass
    foo(foo)   # an empty none() accepts anything
    @typecheck
    def taboo(x: tc.none(tc.has("foo"), tc.has("bar"))):
        pass
    taboo("boofar")
    with expected(InputParameterError("taboo() has got an incompatible value for x: foofar")):
        taboo("foofar")
    with expected(InputParameterError("taboo() has got an incompatible value for x: boobar-ism")):
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
    @typecheck
    def no_tests_please(arg: tc.none(TestCase, classname_contains_Test)): pass
    no_tests_please("stuff")        # OK
    with expected(InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(TestCase())     # Wrong: not wanted here
    with expected(InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(MyCheckers())   # Wrong: superclass not wanted here
    with expected(InputParameterError("no_tests_please() has got an incompatible value for arg: <")):
        no_tests_please(AddressTest())  # Wrong: suspicious class name


def test_custom_exceptions():
    @tc.typecheck_with_exceptions(input_parameter_error = ZeroDivisionError)
    def foo(x: int):
        pass
    with expected(ZeroDivisionError("foo() has got an incompatible value for x: 1")):
        foo("1")
    @tc.typecheck_with_exceptions(return_value_error = MemoryError)
    def foo(x) -> str:
        return x
    with expected(MemoryError):
        foo(1)
    @tc.typecheck_with_exceptions(input_parameter_error = TypeError, return_value_error = TypeError)
    def foo(x: int) -> int:
        return x
    assert foo(1) == 1
    with expected(InputParameterError("typecheck_with_exceptions() has got an incompatible "
                                      "value for input_parameter_error: <class 'int'>")):
        @tc.typecheck_with_exceptions(input_parameter_error = int)
        def foo():
            pass
    with expected(InputParameterError("typecheck_with_exceptions() has got an incompatible "
                                      "value for return_value_error: <class 'int'>")):
        @tc.typecheck_with_exceptions(return_value_error = int)
        def foo():
            pass


def test_disable():
    @typecheck
    def foo(x: int):
        pass
    tc.disable() # disable-only switch, no further proxying is performed
    @typecheck
    def bar(x: int):
        pass
    foo(1)
    with expected(InputParameterError("foo() has got an incompatible value for x: 1")):
        foo("1")
    bar(1)
    bar("1")


# EOF