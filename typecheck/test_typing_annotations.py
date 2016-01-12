import typing as tg

import typecheck as tc
import typecheck.framework as fw
from .testhelper import expected

############################################################################


@tc.typecheck
def foo_Sequence_int_to_Sequence_int(x: tg.Sequence[int], y) -> tg.Sequence[int]:
    x.append(y)
    return x


def test_Sequence_int_with_empty_Sequence():
    assert foo_Sequence_int_to_Sequence_int([], 4) == [4]

def test_Sequence_int_OK():
    assert foo_Sequence_int_to_Sequence_int([1, 2], 4) == [1, 2, 4]

def test_Sequence_int_with_no_Sequence():
    with expected(tc.InputParameterError(
            "foo_Sequence_int_to_Sequence_int() has got an incompatible value for x: 4")):
        foo_Sequence_int_to_Sequence_int(4)

def test_Sequence_int_with_wrong_Sequence():
    with expected(tc.InputParameterError(
            "foo_Sequence_int_to_Sequence_int() has got an incompatible value for x: ['mystring']")):
        foo_Sequence_int_to_Sequence_int(["mystring"], 77)

def test_Sequence_int_with_wrong_result():
    with expected(tc.ReturnValueError(
            "foo_Sequence_int_to_Sequence_int() has returned an incompatible value: [1, '2']")):
        foo_Sequence_int_to_Sequence_int([1], "2")


X = tg.TypeVar('X')  # global type variable, used in various places
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
                      MyGeneric(), MyGeneric("seven"))  # None must be first


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
        assert not ns.is_compatible(X, B)  # not compatible, even as subclass

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

def test_MyGeneric_not_OK():
    for element1 in diverse_collection:
        for element2 in diverse_collection:
            if type(element1) == type(element2):
                continue
            mygen = MyGeneric(element1)
            mygen.append(element1)  # binds X
            with expected(tc.InputParameterError("")):
                print(element1, element2)
                mygen.append(element2)  # violates X binding

