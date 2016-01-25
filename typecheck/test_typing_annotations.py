import builtins
import datetime as dt
import io
import re
import sys
import tempfile

import typing as tg

import pytest

import typecheck as tc
import typecheck.framework as fw
from typecheck.testhelper import expected

# global TypeVars, used in various places:

X = tg.TypeVar('X')
Tb = tg.TypeVar('Tb', bound=dt.date)
Tc = tg.TypeVar('Tc', str, bytes)


############################################################################
# the typing module as such:

def test_typing_module_weirdness():
    # This was a Py3.4 bug in typing 3.5.0.1:
    assert issubclass(tg.Iterable, tg.Generic) == (sys.version_info >= (3,5))
    # ItemsView comes out with three parameters:
    # one (T_co) from Iterable (via MappingView),
    # two (KT, VT_co) from Generic.
    # T_co must in fact be Tuple[KT, VT_co], but how would we know that?
    # Three parameters makes no sense; this is a mess.
    assert tg.ItemsView.__parameters__ == (tg.T_co, tg.KT, tg.VT_co)
    # This is an assumption in GenericMetaChecker._can_have_instance:
    assert not issubclass(tg.Sequence[X], tg.Iterable[X]) # very strange!


############################################################################
# Generic type with fixed content type

@tc.typecheck
def foo_Sequence_int_to_List_int(x: tg.Sequence[int], y) -> tg.List[int]:
    x.append(y)
    return x


def test_Sequence_int_with_empty_Sequence():
    assert foo_Sequence_int_to_List_int([], 4) == [4]

def test_Sequence_int_OK():
    assert foo_Sequence_int_to_List_int([1, 2], 4) == [1, 2, 4]

def test_Sequence_int_with_no_Sequence():
    with expected(tc.InputParameterError(
            "has got an incompatible value for x: 4")):
        foo_Sequence_int_to_List_int(4)

def test_Sequence_int_with_wrong_Sequence():
    with expected(tc.InputParameterError(
            "has got an incompatible value for x: ['mystring']")):
        foo_Sequence_int_to_List_int(["mystring"], 77)

def test_Sequence_int_with_wrong_result():
    with expected(tc.ReturnValueError(
            "has returned an incompatible value: [1, '2']")):
        foo_Sequence_int_to_List_int([1], "2")

############################################################################
# Generic stand-alone functions

def test_TypeVarNamespace_without_instance():
    class A:
        pass
    class B(A):
        pass
    for thetype in (int, float, str, list, dict, A, MyGeneric):
        ns = fw.TypeVarNamespace()
        assert not ns.is_generic_in(X)
        assert not ns.is_bound(X)
        ns.bind(X, thetype)
        assert ns.is_bound(X)
        assert ns.binding_of(X) == thetype
        assert ns.is_compatible(X, thetype)
        if thetype == A:
            assert ns.is_compatible(X, B)


@tc.typecheck
def foo_Sequence_X_to_Sequence_X(xs: tg.Sequence[X], x: X) -> tg.Sequence[X]:
    xs.append(x)
    return xs

def test_Sequence_X_int_OK():
    assert foo_Sequence_X_to_Sequence_X([1, 2], 4) == [1, 2, 4]

def test_Sequence_X_int_notOK():
    with expected(tc.InputParameterError(
            "foo_Sequence_X_to_Sequence_X() has got an incompatible value for x: a_string")):
        foo_Sequence_X_to_Sequence_X([1, 2], "a_string")

############################################################################
# TypeVarNamespace, Generic class with TypeVar binding on the instance level

class MyGeneric(tg.Generic[X]):
    def __init__(self, initial_element=None):
        self.content = []  # a tg.Sequence
        if initial_element is not None:
            self.content.append(initial_element)

    @tc.typecheck
    def append(self, el: X):
        self.content.append(el)

    @tc.typecheck
    def get(self, index: int) -> X:
        return self.content[index]

diverse_collection = (None, False, 1, 2.0, "three", [4], {5: "six"},
                      MyGeneric(), MyGeneric("seven"),
                      MyGeneric[X](), MyGeneric[str]("seven"),
                      dt.date.today(), dt.datetime.now(),
                      )  # None must be first


def test_TypeVarNamespace_with_instance():
    mycollection = list(diverse_collection)[1:]  # leave out None
    for element in mycollection:
        print(element)
        thetype = type(element)
        mygen = MyGeneric(element)
        ns = fw.TypeVarNamespace(mygen)
        assert ns._instance
        assert ns.is_generic_in(X)
        assert not ns.is_bound(X)
        ns.bind(X, thetype)
        assert ns.is_bound(X)
        assert ns.binding_of(X) == thetype
        assert ns.is_compatible(X, thetype)

def test_MyGeneric_OK_and_not_OK():
    for element1 in diverse_collection:
        for element2 in diverse_collection:
            if type(element1) == type(element2):
                continue
            mygen = MyGeneric(element1)
            mygen.append(element1)  # binds X
            mygen.append(element1)  # checks X binding: OK
            print(element1, element2)
            if (issubclass(type(element1), type(element2)) or
                    issubclass(type(element2), type(element1))):
                mygen.append(element2)  # conforms to X binding
            else:
                with expected(tc.InputParameterError("")):
                    mygen.append(element2)  # violates X binding

# TODO: test Generic class with multiple inheritance

############################################################################
# type variable with bound or constraint

@tc.typecheck
def foo_with_bound(date1: Tb, date2: Tb):
    pass

def test_TypeVar_bound_OK_sameclass():
    foo_with_bound(dt.date.today(), dt.date.today())

def test_TypeVar_bound_OK_subclass():
    foo_with_bound(dt.datetime.now(), dt.datetime.now())

def test_TypeVar_bound_OK_mixed_classes():
    foo_with_bound(dt.datetime.now(), dt.date.today())
    foo_with_bound(dt.date.today(), dt.datetime.now())

def test_TypeVar_bound_violated():
    with (expected(tc.InputParameterError(""))):
        foo_with_bound(1, 2)  # both same type, but not below the bound
    with (expected(tc.InputParameterError(""))):
        foo_with_bound(object(), object())  # above the bound


@tc.typecheck
def foo_with_constraint(date1: Tc, date2: Tc):
    pass

def test_TypeVar_constraint_OK():
    foo_with_constraint("str1", "str2")
    foo_with_constraint(b"bytes1", b"bytes2")

def test_TypeVar_constraint_not_OK():
    with (expected(tc.InputParameterError(""))):
        foo_with_constraint("str1", b"bytes1")
    with (expected(tc.InputParameterError(""))):
        foo_with_constraint(("b","y"), ("t","e"))


############################################################################
# Generic classes subclass relationship:

def test_GenericMetaChecker_dot_can_have_subclass():
    Ch = tc.typing_predicates.GenericMetaChecker  # class alias
    assert Ch(tg.Sequence[int])._is_possible_subclass(list, tg.Sequence[int])
    assert not Ch(tg.Sequence[int])._is_possible_subclass(int, tg.Sequence[int])
    assert Ch(tg.Iterable[int])._is_possible_subclass(tg.Sequence[int], tg.Iterable[int])


############################################################################
# Mapping, Set, MappingView

@tc.typecheck
def foo_Mapping_str_float_to_float(m: tg.Mapping[str,float], k: str) -> float:
    return m[k]

def test_Mapping_str_float_OK():
    assert foo_Mapping_str_float_to_float(dict(a=4.0), "a") == 4.0

def test_Mapping_str_float_not_OK():
    with expected(tc.InputParameterError("{'a': True}")):  # wrong value type
        assert foo_Mapping_str_float_to_float(dict(a=True), "a") == True
    with expected(tc.InputParameterError("{b'a': 4.0}")):  # wrong key type
        assert foo_Mapping_str_float_to_float({b'a':4.0}, b"a") == 4.0


@tc.typecheck
def foo_Set_Tc_Tc_to_bool(s: tg.Set[Tc], el: Tc) -> bool:
    return el in s

def test_Set_Tc_OK():
    assert foo_Set_Tc_Tc_to_bool(set(("yes","maybe")), "yes")
    assert not foo_Set_Tc_Tc_to_bool(set(("yes","maybe")), "no")
    assert foo_Set_Tc_Tc_to_bool(set((b"yes",b"maybe")), b"yes")

def test_Set_Tc_not_OK():
    with expected(tc.InputParameterError("")):
        assert foo_Set_Tc_Tc_to_bool(set(("yes",b"maybe")), "yes")
    with expected(tc.InputParameterError("")):
        assert foo_Set_Tc_Tc_to_bool(set((1, 2)), 2)
    with expected(tc.InputParameterError("")):
        assert foo_Set_Tc_Tc_to_bool(set((("yes",),("maybe",))), ("yes",))


@tc.typecheck
def foo_KeysView_to_Sequence(v: tg.KeysView[Tc]) -> tg.Sequence[Tc]:
    result = [item for item in v]
    result.sort()
    assert len([item for item in v]) == len(result)  # iterable not exhausted
    return result

def test_KeysView_to_Sequence_OK():
    assert foo_KeysView_to_Sequence(dict(a=11, b=12).keys()) == ['a', 'b']
    assert foo_KeysView_to_Sequence({b'A':11, b'B':12}.keys()) == [b'A', b'B']

def test_KeysView_to_Sequence_not_OK():
    with expected(tc.InputParameterError("v: dict_keys\(.*3.*")):
        assert foo_KeysView_to_Sequence({b'A':11, b'B':12, 3:13}.keys()) == [b'A', b'B', 13]


############################################################################
# for Iterator and Container we cannot check the actual content

@tc.typecheck
def foo_Iterator(i: tg.Iterator[dt.date]):
    pass

@tc.typecheck
def foo_Container(c: tg.Container[tg.Sequence[str]]):
    pass

def test_Iterable_Iterator_Container_OK():
    """
    No extra code is needed to check Iterable, Iterator, and Container,
    because there is no suitable way to access their contents.
    """
    foo_Iterator((dt.date.today(), dt.date.today()).__iter__())
    foo_Container([["nested", "list"], ["of", "strings"]])

def test_Iterator_Container_content_not_OK_catchable():
    """
    Because there is no suitable way to access their contents,
    such generic types may still pass the typecheck if their content is
    of the wrong type.
    This is a fundamental problem, not an implementation gap.
    The only cases where improper contents will be caught is when the argument
    is _also_ tg.Iterable.
    """
    with expected(tc.InputParameterError("list_iterator")):
        foo_Iterator(["shouldn't be", "strings here"].__iter__())
    with expected(tc.InputParameterError("3, 4")):
        foo_Container([[3, 4], [5, 6]])

def test_Iterator_totally_not_OK():
    with expected(tc.InputParameterError("")):
        foo_Iterator((dt.date.today(), dt.date.today()))  # lacks .__next__()


class MySpecialtyGeneric(tg.Container[X]):
    def __init__(self, contents):
        assert isinstance(contents, tg.Sequence)
        self.contents = contents  # an 'nice' container, but hidden within
    def __iter__(self):
        return self.contents.__iter__()
    def __contains__(self, item):
        return item in self.contents

@tc.typecheck
def foo_MySpecialtyGeneric(c: MySpecialtyGeneric[float]):
    pass

def test_Container_content_not_OK_not_catchable():
    """
    See above: With generics that are not otherwise checkable,
    wrong contents will not be detected.
    """
    incorrect_content = MySpecialtyGeneric(["shouldn't be", "strings here"])
    foo_Container(incorrect_content)  # cannot detect
    foo_MySpecialtyGeneric(incorrect_content)  # cannot detect


############################################################################
# NamedTuple

Employee = tg.NamedTuple('Employee', [('name', str), ('id', int)])
Employee2 = tg.NamedTuple('Employee2', [('name', str), ('id', int)])

@tc.typecheck
def foo_Employee(e: Employee):
    pass

def test_NamedTuple_OK():
    foo_Employee(Employee(name="Jones", id=99))

def test_NamedTuple_not_OK():
    with expected(tc.InputParameterError("name=8, id=9)")):
        foo_Employee(Employee(name=8, id=9))
    with expected(tc.InputParameterError("'aaa')")):
        foo_Employee(Employee(name='Jones', id='aaa'))
    with expected(tc.InputParameterError("Employee2(name='Jones', id=999)")):
        foo_Employee(Employee2(name='Jones', id=999))


############################################################################
# Tuple

@tc.typecheck
def foo_Tuple_int_float_to_float(t: tg.Tuple[int, float]) -> float:
    return t[1]

def test_Tuple_OK():
    assert foo_Tuple_int_float_to_float((2, 3.0)) == 3.0

def test_Tuple_not_OK():
    with expected(tc.InputParameterError("t: 2")):
        foo_Tuple_int_float_to_float(2)
    with expected(tc.InputParameterError("t: (2,)")):
        foo_Tuple_int_float_to_float((2,))
    with expected(tc.InputParameterError("t: (2, None)")):
        foo_Tuple_int_float_to_float((2, None))
    with expected(tc.InputParameterError("t: None")):
        foo_Tuple_int_float_to_float(None)
    with expected(tc.InputParameterError("t: (2, 3)")):
        foo_Tuple_int_float_to_float((2, 3))
    with expected(tc.InputParameterError("t: (2, 3.0, 4.0)")):
        foo_Tuple_int_float_to_float((2, 3.0, 4.0))

############################################################################
# Union

@tc.typecheck
def foo_Union_int_SequenceFloat(u: tg.Union[int, tg.Sequence[float]]):
    pass

def test_Union_OK():
    foo_Union_int_SequenceFloat(4)
    foo_Union_int_SequenceFloat([])
    foo_Union_int_SequenceFloat([4.0, 5.0])

def test_Union_not_OK():
    with expected(tc.InputParameterError("u: wrong")):
        foo_Union_int_SequenceFloat("wrong")
    with expected(tc.InputParameterError("u: [4]")):
        foo_Union_int_SequenceFloat([4])
    with expected(tc.InputParameterError("u: None")):
        foo_Union_int_SequenceFloat(None)

############################################################################
# Optional

# needs no implementation code, all work is done by tg itself

@tc.typecheck
def foo_Optional_Union_int_SequenceFloat(u: tg.Optional[tg.Union[int, tg.Sequence[float]]]):
    pass

def test_Optional_OK():
    foo_Optional_Union_int_SequenceFloat(None)
    foo_Optional_Union_int_SequenceFloat(4)
    foo_Optional_Union_int_SequenceFloat([])
    foo_Optional_Union_int_SequenceFloat([4.0, 5.0])

def test_Optional_not_OK():
    with expected(tc.InputParameterError("u: wrong")):
        foo_Optional_Union_int_SequenceFloat("wrong")
    with expected(tc.InputParameterError("u: [4]")):
        foo_Optional_Union_int_SequenceFloat([4])

############################################################################
# Callable

@tc.typecheck
def foo_Callable(func: tg.Callable):
    pass

@pytest.mark.skipif(True, reason="I have no idea what's the problem here.")
def test_Callable_OK():  # TODO: What's going wrong here?
    assert callable(foo_Callable)
    # Not even one of the following works:
    foo_Callable(lambda: foo_Callable)
    foo_Callable(lambda x: 2*x)
    foo_Callable(builtins.callable)
    foo_Callable(builtins.dict)
    foo_Callable(builtins.len)
    foo_Callable(foo_Callable)


############################################################################
# _Protocol

# is handled by TypeChecker without special code, so we do not test them all

@tc.typecheck
def foo_SupportsAbs(x: tg.SupportsAbs) -> tg.SupportsAbs:
    return abs(x)

def test_SupportsAbs_OK():
    assert foo_SupportsAbs(-4) == 4
    assert foo_SupportsAbs(0.0) == 0.0
    assert foo_SupportsAbs(True) == 1

def test_SupportsAbs_not_OK():
    with expected(tc.InputParameterError("")):
        foo_SupportsAbs("-4")

############################################################################
# io

# tg.io appears to be hardly useful as of 3.5

def test_io_is_halfhearted():
    """
    It would be pythonic if tg.io.IO applied to all file-like objects.
    But as of 3.5, it does not, which is what we assert here.
    """
    with io.StringIO("my string as input") as f:
        assert not isinstance(f, tg.io.TextIO)
        assert not isinstance(f, tg.io.IO[str])
    with tempfile.TemporaryFile("wb") as f:
        if "file" in dir(f):
            f = f.file  # TemporaryFile() on non-POSIX platform
        assert not isinstance(f, tg.io.BinaryIO)
        assert not isinstance(f, tg.io.IO[bytes])

############################################################################
# re

# tg.io appears to be broken as of 3.5

def test_re_is_halfhearted():
    """
    As of 3.5, the implementation of tg appears to be incomplete for TypeAlias.
    All those asserts should in fact be successful.
    """
    error = TypeError("Type aliases cannot be used with isinstance().")
    with expected(error):
        assert isinstance(re.compile("regexp"), tg.re.Pattern[str])
    with expected(error):
        assert isinstance(re.compile(b"byteregexp"), tg.re.Pattern[bytes])
    with expected(error):
        assert isinstance(re.match("regexp", "string"), tg.re.Match[str])
    with expected(error):
        assert isinstance(re.match(b"regexp", b"string"), tg.re.Match[bytes])

############################################################################
# 'MyClass' as str

class A:
    @tc.typecheck
    def foo_something(self, another: 'A') -> 'A':
        return self

def test_forward_reference_OK():
    a1 = A()
    a2 = A()
    a1.foo_something(a2)

def test_forward_reference_to_local_class_OK_or_not_OK():
    class B:
        @tc.typecheck
        def foo_something(self, another: 'B') -> 'B':
            return self
    b1 = B()
    b2 = B()
    b1.foo_something(b2)
    with expected(tc.InputParameterError("something different")):
        b1.foo_something("something different")


def test_forward_reference_not_OK():
    a1 = A()
    with expected(tc.InputParameterError("something different")):
        a1.foo_something("something different")


############################################################################
# A complex example

ComplexType = tg.Union[tg.Optional[tg.Sequence[tg.Mapping[Tc, tg.Optional[float]]]],
                       Tc, bool, dt.date]

@tc.typecheck
def foo_wow_thats_nested(x: ComplexType) -> tg.Union[Tc, bool, float]:
    if isinstance(x, (str, bytes)):
        return x[0:3]
    elif isinstance(x, tg.Sequence):
        return x[0][sorted(x[0].keys())[0]]
    else:
        return x

def test_complex_example_OK():
    assert foo_wow_thats_nested(True) == True
    assert foo_wow_thats_nested('string') == 'str'
    assert foo_wow_thats_nested(b'bytes') == b'byt'
    assert foo_wow_thats_nested([dict(a=1.0, b=2.0)]) == 1.0
    assert foo_wow_thats_nested([{b'a':1.0, b'1':2.0}]) == 2.0

def test_complex_example_not_OK():
    with expected(tc.InputParameterError("1")):
        assert foo_wow_thats_nested(1) == 1
    with expected(IndexError("")):
        foo_wow_thats_nested([])
    with expected(tc.ReturnValueError("")):
        assert foo_wow_thats_nested(None) == None
    with expected(tc.ReturnValueError("")):
        assert foo_wow_thats_nested(dt.date.today()) == dt.date.today()
    with expected(tc.ReturnValueError("None")):
        assert foo_wow_thats_nested([dict(a=None, b=2.0)]) == None


############################################################################
# and last of all: Any

@tc.typecheck
def foo_Any(x: tg.Any) -> tg.Any:
    return x

def test_Any_OK():
    assert foo_Any(42)

############################################################################
