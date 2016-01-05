import typing as tg

import typecheck as tc
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


X = tg.TypeVar('X')
@tc.typecheck
def foo_Sequence_X_to_Sequence_X(xs: tg.Sequence[X], x: X) -> tg.Sequence[X]:
    x.append(y)
    return x

def test_Sequence_X_int_OK():
    assert foo_Sequence_X_to_Sequence_X([1, 2], 4) == [1, 2, 4]

