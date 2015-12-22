# Most of this file is from the lower part of Dmitry Dvoinikov's
# http://www.targeted.org/python/recipes/typecheck3000.py
# reworked into py.test tests

import random
import re
import time
from traceback import extract_stack

import typecheck as tc
import typecheck.framework
from .testhelper import expected

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
            pass  # this is a Python3 way of saying sys.exc_clear()

    def __exit__(self, exc_type, exc_value, traceback):
        assert exc_type is not None, \
            "expected {0:s} to have been thrown".format(self._type.__name__)
        msg = str(exc_value)
        return (issubclass(exc_type, self._type) and
                (self._msg is None or
                 msg.startswith(self._msg) or  # for instance
                 re.match(self._msg, msg)))  # for class + regexp


############################################################################


def test_wrapped_function_keeps_its_name():
    @tc.typecheck
    def foo() -> type(None):
        pass

    print("method proxy naming")
    assert foo.__name__ == "foo"


def test_no_excessive_proxying():
    @tc.typecheck
    def foo():
        assert extract_stack()[-2][2] != "typecheck_invocation_proxy"

    foo()

    @tc.typecheck
    def bar() -> type(None):
        assert extract_stack()[-2][2] == "typecheck_invocation_proxy"

    bar()


def test_double_annotations_wrapping():
    @tc.typecheck
    def foo(x: int):
        return x

    assert foo(1) == tc.typecheck(foo)(1) == 1


def test_empty_string_in_incompatible_values():
    @tc.typecheck
    def foo(s: lambda s: s != ""=None):
        return s

    assert foo() is None
    assert foo(None) is None
    assert foo(0) == 0
    with expected(tc.InputParameterError("foo() has got an incompatible value for s: ''")):
        foo("")

    @tc.typecheck
    def foo(*, k: typecheck.framework.optional(lambda s: s != "")=None):
        return k

    assert foo() is None
    assert foo(k=None) is None
    assert foo(k=0) == 0
    with expected(tc.InputParameterError("foo() has got an incompatible value for k: ''")):
        foo(k="")

    @tc.typecheck
    def foo(s=None) -> lambda s: s != "":
        return s

    assert foo() is None
    assert foo(None) is None
    assert foo(0) == 0
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: ''")):
        foo("")


def test_invalid_type_specification():
    with expected(tc.TypeCheckSpecificationError("invalid typecheck for a")):
        @tc.typecheck
        def foo(a: 10):
            pass
    with expected(tc.TypeCheckSpecificationError("invalid typecheck for k")):
        @tc.typecheck
        def foo(*, k: 10):
            pass
    with expected(tc.TypeCheckSpecificationError("invalid typecheck for return")):
        @tc.typecheck
        def foo() -> 10:
            pass


def test_incompatible_default_value():
    with expected(tc.TypeCheckSpecificationError("the default value for b is incompatible with its typecheck")):
        @tc.typecheck
        def ax_b2(a, b: int="two"):
            pass
    with expected(tc.TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @tc.typecheck
        def a1_b2(a: int="one", b="two"):
            pass
    with expected(tc.TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @tc.typecheck
        def foo(a: str=None):
            pass
    with expected(tc.TypeCheckSpecificationError("the default value for a is incompatible with its typecheck")):
        @tc.typecheck
        def kw(*, a: int=1.0):
            pass
    with expected(tc.TypeCheckSpecificationError("the default value for b is incompatible with its typecheck")):
        @tc.typecheck
        def kw(*, a: int=1, b: str=10):
            pass


def test_can_change_default_value():
    @tc.typecheck
    def foo(a: list=[]):
        a.append(len(a))
        return a

    assert foo() == [0]
    assert foo() == [0, 1]
    assert foo([]) == [0]
    assert foo() == [0, 1, 2]
    assert foo() == [0, 1, 2, 3]

    @tc.typecheck
    def foo(*, k: typecheck.framework.optional(list)=[]):
        k.append(len(k))
        return k

    assert foo() == [0]
    assert foo() == [0, 1]
    assert foo(k=[]) == [0]
    assert foo() == [0, 1, 2]
    assert foo() == [0, 1, 2, 3]


def test_unchecked_args():
    @tc.typecheck
    def axn_bxn(a, b):
        return a + b

    assert axn_bxn(10, 20) == 30
    assert axn_bxn(10, 20.0) == 30.0
    assert axn_bxn(10.0, 20) == 30.0
    assert axn_bxn(10.0, 20.0) == 30.0
    with expected(TypeError, "axn_bxn"):
        axn_bxn(10)
    with expected(TypeError, "axn_bxn"):
        axn_bxn()


def test_default_unchecked_args1():
    @tc.typecheck
    def axn_b2n(a, b=2):
        return a + b

    assert axn_b2n(10, 20) == 30
    assert axn_b2n(10, 20.0) == 30.0
    assert axn_b2n(10.0, 20) == 30.0
    assert axn_b2n(10.0, 20.0) == 30.0
    assert axn_b2n(10) == 12
    assert axn_b2n(10.0) == 12.0
    with expected(TypeError, "axn_b2n"):
        axn_b2n()


def test_default_unchecked_args2():
    @tc.typecheck
    def a1n_b2n(a=1, b=2):
        return a + b

    assert a1n_b2n(10, 20) == 30
    assert a1n_b2n(10, 20.0) == 30.0
    assert a1n_b2n(10.0, 20) == 30.0
    assert a1n_b2n(10.0, 20.0) == 30.0
    assert a1n_b2n(10) == 12
    assert a1n_b2n(10.0) == 12.0
    assert a1n_b2n() == 3


def test_simple_checked_args1():
    @tc.typecheck
    def axc_bxn(a: int, b):
        return a + b

    assert axc_bxn(10, 20) == 30
    assert axc_bxn(10, 20.0) == 30.0
    with expected(tc.InputParameterError("axc_bxn() has got an incompatible value for a: 10.0")):
        axc_bxn(10.0, 20)
    with expected(tc.InputParameterError("axc_bxn() has got an incompatible value for a: 10.0")):
        axc_bxn(10.0, 20.0)
    with expected(TypeError, "axc_bxn"):
        axc_bxn(10)
    with expected(TypeError, "axc_bxn"):
        axc_bxn()


def test_simple_checked_args2():
    @tc.typecheck
    def axn_bxc(a, b: int):
        return a + b

    assert axn_bxc(10, 20) == 30
    with expected(tc.InputParameterError("axn_bxc() has got an incompatible value for b: 20.0")):
        axn_bxc(10, 20.0)
    assert axn_bxc(10.0, 20) == 30.0
    with expected(tc.InputParameterError("axn_bxc() has got an incompatible value for b: 20.0")):
        axn_bxc(10.0, 20.0)
    with expected(TypeError, "axn_bxc"):
        axn_bxc(10)
    with expected(TypeError, "axn_bxc"):
        axn_bxc()


def test_simple_default_checked_args1():
    @tc.typecheck
    def axn_b2c(a, b: int=2):
        return a + b

    assert axn_b2c(10, 20) == 30
    with expected(tc.InputParameterError("axn_b2c() has got an incompatible value for b: 20.0")):
        axn_b2c(10, 20.0)
    assert axn_b2c(10.0, 20) == 30.0
    with expected(tc.InputParameterError("axn_b2c() has got an incompatible value for b: 20.0")):
        axn_b2c(10.0, 20.0)
    assert axn_b2c(10) == 12
    assert axn_b2c(10.0) == 12.0
    with expected(TypeError, "axn_b2c"):
        axn_b2c()


def test_simple_default_checked_args2():
    @tc.typecheck
    def a1n_b2c(a=1, b: int=2):
        return a + b

    assert a1n_b2c(10, 20) == 30
    with expected(tc.InputParameterError("a1n_b2c() has got an incompatible value for b: 20.0")):
        a1n_b2c(10, 20.0)
    assert a1n_b2c(10.0, 20) == 30.0
    with expected(tc.InputParameterError("a1n_b2c() has got an incompatible value for b: 20.0")):
        a1n_b2c(10.0, 20.0)
    assert a1n_b2c(10) == 12
    assert a1n_b2c(10.0) == 12.0
    assert a1n_b2c() == 3


def test_simple_default_checked_args3():
    @tc.typecheck
    def axc_b2n(a: int, b=2):
        return a + b

    assert axc_b2n(10, 20) == 30
    assert axc_b2n(10, 20.0) == 30.0
    with expected(tc.InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0, 20)
    with expected(tc.InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0, 20.0)
    assert axc_b2n(10) == 12
    with expected(tc.InputParameterError("axc_b2n() has got an incompatible value for a: 10.0")):
        axc_b2n(10.0)
    with expected(TypeError, "axc_b2n"):
        axc_b2n()


def test_simple_default_checked_args4():
    @tc.typecheck
    def a1c_b2n(a: int=1, b=2):
        return a + b

    assert a1c_b2n(10, 20) == 30
    assert a1c_b2n(10, 20.0) == 30.0
    with expected(tc.InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0, 20)
    with expected(tc.InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0, 20.0)
    assert a1c_b2n(10) == 12
    with expected(tc.InputParameterError("a1c_b2n() has got an incompatible value for a: 10.0")):
        a1c_b2n(10.0)
    assert a1c_b2n() == 3


def test_simple_checked_args3():
    @tc.typecheck
    def axc_bxc(a: int, b: int):
        return a + b

    assert axc_bxc(10, 20) == 30
    with expected(tc.InputParameterError("axc_bxc() has got an incompatible value for b: 20.0")):
        axc_bxc(10, 20.0)
    with expected(tc.InputParameterError("axc_bxc() has got an incompatible value for a: 10.0")):
        axc_bxc(10.0, 20)
    with expected(tc.InputParameterError("axc_bxc() has got an incompatible value for a: 10.0")):
        axc_bxc(10.0, 20.0)
    with expected(TypeError, "axc_bxc"):
        axc_bxc(10)
    with expected(TypeError, "axc_bxc"):
        axc_bxc()


def test_simple_default_checked_args5():
    @tc.typecheck
    def axc_b2c(a: int, b: int=2):
        return a + b

    assert axc_b2c(10, 20) == 30
    with expected(tc.InputParameterError("axc_b2c() has got an incompatible value for b: 20.0")):
        axc_b2c(10, 20.0)
    with expected(tc.InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0, 20)
    with expected(tc.InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0, 20.0)
    assert axc_b2c(10) == 12
    with expected(tc.InputParameterError("axc_b2c() has got an incompatible value for a: 10.0")):
        axc_b2c(10.0)
    with expected(TypeError, "axc_b2c"):
        axc_b2c()


def test_simple_default_checked_args6():
    @tc.typecheck
    def a1c_b2c(a: int=1, b: int=2):
        return a + b

    assert a1c_b2c(10, 20) == 30
    with expected(tc.InputParameterError("a1c_b2c() has got an incompatible value for b: 20.0")):
        a1c_b2c(10, 20.0)
    with expected(tc.InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0, 20)
    with expected(tc.InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0, 20.0)
    assert a1c_b2c(10) == 12
    with expected(tc.InputParameterError("a1c_b2c() has got an incompatible value for a: 10.0")):
        a1c_b2c(10.0)
    assert a1c_b2c() == 3


############################################################################

def test_default_vs_checked_args_random_generated():
    test_passes = 0
    start = time.time()
    while time.time() < start + 1.0:
        N = random.randint(1, 10)
        DN = random.randint(0, N)
        args = ["a{0:03d}".format(i) for i in range(N)]
        chkd = [random.randint(0, 1) for i in range(N)]
        deft = [i >= DN for i in range(N)]
        def_args = ", ".join(map(lambda x: "{0}{1}{2}".format(x[1][0], x[1][1] and ": int" or "",
                                                              x[1][2] and " = {0}".format(x[0]) or ""),
                                 enumerate(zip(args, chkd, deft))))
        sum_args = " + ".join(args)
        test = "@tc.typecheck\n" \
               "def some_func({def_args}):\n" \
               "    return {sum_args}\n"
        for provided_args in range(DN, N + 1):
            success_args = [j * 10 for j in range(provided_args)]
            success_result = provided_args * (provided_args - 1) * 9 // 2 + N * (N - 1) // 2
            test_run = test
            test_run += "assert some_func({success_args}) == {success_result}\n"
            failure_args = [j for (j, c) in enumerate(chkd) if j < provided_args and c]
            if failure_args:
                random.shuffle(failure_args)
                failure_arg = failure_args[0]
                failure_value = failure_arg * 10.0
                failure_args = success_args[:]
                failure_args[failure_arg] = failure_value
                test_run += "with expected(tc.InputParameterError('some_func() has got an " \
                            "incompatible value for a{failure_arg:03d}: {failure_value}')):\n" \
                            "    some_func({failure_args})\n"
                failure_args = ", ".join(map(str, failure_args))

            success_args = ", ".join(map(str, success_args))
            exec(test_run.format(**locals()))
            test_passes += 1
    print("{0} tests passed ok".format(test_passes))


############################################################################

def test_default_vs_checked_kwargs1():
    @tc.typecheck
    def foo(*, a: str):
        return a

    with expected(tc.InputParameterError("foo() has got an incompatible value for a: <no value>")):
        foo()
    assert foo(a="b") == "b"


def test_default_vs_checked_kwargs2():
    @tc.typecheck
    def foo(*, a: typecheck.framework.optional(str)= "a"):
        return a

    assert foo() == "a"
    assert foo(a="b") == "b"
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: 10")):
        foo(a=10)


def test_default_vs_checked_kwargs3():
    @tc.typecheck
    def pxn_qxn(*, p, q, **kwargs):
        return p + q

    assert pxn_qxn(p=1, q=2) == 3
    assert pxn_qxn(p=1, q=2.0) == 3.0
    assert pxn_qxn(p=1.0, q=2) == 3.0
    assert pxn_qxn(p=1.0, q=2.0) == 3.0
    with expected(TypeError, "pxn_qxn"):
        pxn_qxn(p=1)
    with expected(TypeError, "pxn_qxn"):
        pxn_qxn(q=2)
    with expected(TypeError, "pxn_qxn"):
        pxn_qxn()


def test_default_vs_checked_kwargs4():
    @tc.typecheck
    def pxn_q2n(*, p, q=2):
        return p + q

    assert pxn_q2n(p=1, q=2) == 3
    assert pxn_q2n(p=1, q=2.0) == 3.0
    assert pxn_q2n(p=1.0, q=2) == 3.0
    assert pxn_q2n(p=1.0, q=2.0) == 3.0
    assert pxn_q2n(p=1) == 3
    with expected(TypeError, "pxn_q2n"):
        pxn_q2n(q=2)
    with expected(TypeError, "pxn_q2n"):
        pxn_q2n()


def test_default_vs_checked_kwargs5():
    @tc.typecheck
    def p1n_q2n(*, p=1, q=2):
        return p + q

    assert p1n_q2n(p=1, q=2) == 3
    assert p1n_q2n(p=1, q=2.0) == 3.0
    assert p1n_q2n(p=1.0, q=2) == 3.0
    assert p1n_q2n(p=1.0, q=2.0) == 3.0
    assert p1n_q2n(p=1) == 3
    assert p1n_q2n(q=2) == 3
    assert p1n_q2n() == 3


def test_default_vs_checked_kwargs6():
    @tc.typecheck
    def pxn_qxc(*, p, q: int):
        return p + q

    assert pxn_qxc(p=1, q=2) == 3
    with expected(tc.InputParameterError("pxn_qxc() has got an incompatible value for q: 2.0")):
        pxn_qxc(p=1, q=2.0)
    assert pxn_qxc(p=1.0, q=2) == 3.0
    with expected(tc.InputParameterError("pxn_qxc() has got an incompatible value for q: 2.0")):
        pxn_qxc(p=1.0, q=2.0)
    with expected(tc.InputParameterError("pxn_qxc() has got an incompatible value for q: <no value>")):
        pxn_qxc(p=1)
    with expected(TypeError, "pxn_qxc"):
        pxn_qxc(q=2)
    with expected(tc.InputParameterError("pxn_qxc() has got an incompatible value for q: <no value>")):
        pxn_qxc()


def test_default_vs_checked_kwargs7():
    @tc.typecheck
    def pxn_q2c(*, p, q: int=2):
        return p + q

    assert pxn_q2c(p=1, q=2) == 3
    with expected(tc.InputParameterError("pxn_q2c() has got an incompatible value for q: 2.0")):
        pxn_q2c(p=1, q=2.0)
    assert pxn_q2c(p=1.0, q=2) == 3.0
    with expected(tc.InputParameterError("pxn_q2c() has got an incompatible value for q: 2.0")):
        pxn_q2c(p=1.0, q=2.0)
    with expected(tc.InputParameterError("pxn_q2c() has got an incompatible value for q: <no value>")):
        pxn_q2c(p=1)
    with expected(TypeError, "pxn_q2c"):
        pxn_q2c(q=2)
    with expected(tc.InputParameterError("pxn_q2c() has got an incompatible value for q: <no value>")):
        pxn_q2c()


def test_default_vs_checked_kwargs8():
    @tc.typecheck
    def p1n_q2c(*, p=1, q: int=2):
        return p + q

    assert p1n_q2c(p=1, q=2) == 3
    with expected(tc.InputParameterError("p1n_q2c() has got an incompatible value for q: 2.0")):
        p1n_q2c(p=1, q=2.0)
    assert p1n_q2c(p=1.0, q=2) == 3.0
    with expected(tc.InputParameterError("p1n_q2c() has got an incompatible value for q: 2.0")):
        p1n_q2c(p=1.0, q=2.0)
    with expected(tc.InputParameterError("p1n_q2c() has got an incompatible value for q: <no value>")):
        p1n_q2c(p=1)
    assert p1n_q2c(q=2) == 3
    with expected(tc.InputParameterError("p1n_q2c() has got an incompatible value for q: <no value>")):
        p1n_q2c()


def test_default_vs_checked_kwargs9():
    @tc.typecheck
    def pxc_qxc(*, p: int, q: int):
        return p + q

    assert pxc_qxc(p=1, q=2) == 3
    with expected(tc.InputParameterError("pxc_qxc() has got an incompatible value for q: 2.0")):
        pxc_qxc(p=1, q=2.0)
    with expected(tc.InputParameterError("pxc_qxc() has got an incompatible value for p: 1.0")):
        pxc_qxc(p=1.0, q=2)
    with expected(tc.InputParameterError,
                  "pxc_qxc\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        pxc_qxc(p=1.0, q=2.0)
    with expected(tc.InputParameterError("pxc_qxc() has got an incompatible value for q: <no value>")):
        pxc_qxc(p=1)
    with expected(tc.InputParameterError("pxc_qxc() has got an incompatible value for p: <no value>")):
        pxc_qxc(q=2)
    with expected(tc.InputParameterError,
                  "pxc_qxc\(\) has got an incompatible value for [pq]: <no value>"):
        pxc_qxc()


def test_default_vs_checked_kwargs10():
    @tc.typecheck
    def pxc_q2c(*, p: int, q: int=2):
        return p + q

    assert pxc_q2c(p=1, q=2) == 3
    with expected(tc.InputParameterError("pxc_q2c() has got an incompatible value for q: 2.0")):
        pxc_q2c(p=1, q=2.0)
    with expected(tc.InputParameterError("pxc_q2c() has got an incompatible value for p: 1.0")):
        pxc_q2c(p=1.0, q=2)
    with expected(tc.InputParameterError,
                  "pxc_q2c\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        pxc_q2c(p=1.0, q=2.0)
    # TODO: should tc.optional() be required when a default is given? No! (also elsewhere)
    with expected(tc.InputParameterError("pxc_q2c() has got an incompatible value for q: <no value>")):
        pxc_q2c(p=1)
    with expected(tc.InputParameterError("pxc_q2c() has got an incompatible value for p: <no value>")):
        pxc_q2c(q=2)


def test_default_vs_checked_kwargs11():
    @tc.typecheck
    def p1c_q2c(*, p: int=1, q: int=2):
        return p + q

    assert p1c_q2c(p=1, q=2) == 3
    with expected(tc.InputParameterError("p1c_q2c() has got an incompatible value for q: 2.0")):
        p1c_q2c(p=1, q=2.0)
    with expected(tc.InputParameterError("p1c_q2c() has got an incompatible value for p: 1.0")):
        p1c_q2c(p=1.0, q=2)
    with expected(tc.InputParameterError,
                  "p1c_q2c\(\) has got an incompatible value for (p: 1.0|q: 2.0)"):
        p1c_q2c(p=1.0, q=2.0)
    with expected(tc.InputParameterError("p1c_q2c() has got an incompatible value for q: <no value>")):
        p1c_q2c(p=1)
    with expected(tc.InputParameterError("p1c_q2c() has got an incompatible value for p: <no value>")):
        p1c_q2c(q=2)

############################################################################

def test_named_arguments():
    @tc.typecheck
    def func(a: int):
        return a

    # test named arguments when value matches expected type
    assert func(5) == 5
    nonsense = 4711
    assert func(a=10) == 10

    # test named arguments when value doesn't match expected type
    class SomeClass: pass
    with expected(tc.InputParameterError("func() has got an incompatible value for a: ['1']")):
        func(a=['1'])
    #with expected(tc.InputParameterError("func() has got an incompatible value for a: ['1']")):
    #    func(a=SomeClass())


def test_named_arguments_with_default():
    @tc.typecheck
    def func(a: int=5):
        return a

    # test named arguments when value matches expected type
    assert func() == 5
    assert func(10) == 10
    assert func(a=15) == 15

    # test named arguments when value doesn't match expected type
    with expected(tc.InputParameterError("func() has got an incompatible value for a: 1")):
        func(a='1')

############################################################################

def test_default_vs_checked_kwargs_randomly_generated():
    test_passes = 0
    start = time.time()
    while time.time() < start + 1.0:
        N = random.randint(1, 10)
        kwrs = ["k{0:03d}".format(i) for i in range(N)]
        chkd = [random.randint(0, 1) for i in range(N)]
        deft = [random.randint(0, 1) for i in range(N)]
        def_kwrs = ", ".join("{0}{1}{2}".format(k, c and ": tc.optional(int)" or "", d and " = {0}".format(i) or "")
                             for (i, (k, c, d)) in enumerate(zip(kwrs, chkd, deft)))
        sum_kwrs = " + ".join(kwrs)
        test = "@tc.typecheck\n" \
               "def some_func(*, {def_kwrs}):\n" \
               "    return {sum_kwrs}\n"
        for i in range(N):
            success_kwrs = {k: i * 10 for (i, (k, c, d)) in enumerate(zip(kwrs, chkd, deft))
                            if (not d) or random.randint(0, 1)}
            temp_kwrs = success_kwrs.copy()
            temp_kwrs.update({k: i for (i, (k, d)) in enumerate(zip(kwrs, deft))
                              if d and k not in success_kwrs})
            success_result = sum(temp_kwrs.values())
            test_run = test
            test_run += "kwargs = {success_kwrs}\n" \
                        "assert some_func(**kwargs) == {success_result}\n"
            failure_kwrs = success_kwrs.copy()
            for k, v in failure_kwrs.items():
                if chkd[int(k[1:])] and random.randint(0, 1):
                    failure_kwarg = k
                    failure_value = float(v)
                    failure_kwrs[failure_kwarg] = failure_value
                    test_run += "kwargs = {failure_kwrs}\n" \
                                "with expected(tc.InputParameterError('some_func() has got an " \
                                "incompatible value for {failure_kwarg}: {failure_value}')):\n" \
                                "    some_func(**kwargs)\n"
                    break
            exec(test_run.format(**locals()))
            test_passes += 1


############################################################################

def test_TypeChecker():
    @tc.typecheck
    def foo(a: int) -> object:
        return a

    assert foo(10) == 10

    @tc.typecheck
    def foo(*args, a: str) -> float:
        return float(a)

    assert foo(a="10.0") == 10.0

    class Foo():
        pass

    class Bar(Foo):
        pass

    @tc.typecheck
    def foo(a: Bar) -> Foo:
        return a

    f = Bar()
    assert foo(f) is f
    f = Foo()
    with expected(tc.InputParameterError("foo() has got an incompatible value for a: <")):
        foo(f)

    @tc.typecheck
    def foo(a: Foo) -> Bar:
        return a

    f = Bar()
    assert foo(f) is f
    f = Foo()
    with expected(tc.ReturnValueError("foo() has returned an incompatible value: <")):
        foo(f)

############################################################################

def test_custom_exceptions():
    @tc.typecheck_with_exceptions(input_parameter_error=ZeroDivisionError)
    def foo(x: int):
        pass

    with expected(ZeroDivisionError("foo() has got an incompatible value for x: 1")):
        foo("1")

    @tc.typecheck_with_exceptions(return_value_error=MemoryError)
    def foo(x) -> str:
        return x

    with expected(MemoryError):
        foo(1)

    @tc.typecheck_with_exceptions(input_parameter_error=TypeError, return_value_error=TypeError)
    def foo(x: int) -> int:
        return x

    assert foo(1) == 1


def test_disable():
    @tc.typecheck
    def foo(x: int):
        pass

    tc.disable()  # disable-only switch, no further proxying is performed
    try:
        @tc.typecheck
        def bar(x: int):
            pass

        foo(1)
        with expected(tc.InputParameterError("foo() has got an incompatible value for x: 1")):
            foo("1")
        bar(1)
        bar("1")
    finally:
        tc.enable()  # make sure typecheck continues to work!


############################################################################


# EOF
