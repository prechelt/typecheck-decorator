A decorator for functions, ``@tc.typecheck``, to be used together with
Python3 annotations on function parameters and function results.
The decorator will perform dynamic argument type checking for every call to the function.

::

  @tc.typecheck
  def foo1(a:int, b=None, c:str="mydefault") -> bool :
      print(a, b, c)
      return b is not None and a != b

The parts ``:int``, ``:str``, and ``-> bool`` are annotations.
This is a syntactic feature introduced in Python 3 where ``:`` (for parameters)
and ``->`` (for results) are delimiters and the rest can be
an arbitrary expression.
It is important to understand that, as such,
*annotations do not have any semantics whatsoever*.
There must be explicit Python code somewhere
that looks at them and does something in order to give them a meaning.


The ``@tc.typecheck`` decorator gives the above annotations the following meaning:
``foo1``'s argument ``a`` must have type ``int``,
``b`` has no annotation and can have any type whatsoever, it will not be checked,
``c`` must have type string,
and the function's result must be either
``True`` (not ``17`` or ``"yes"`` or ``[3,7,44]`` or some such) or
``False`` (not ``0`` or ``None`` or ``[]`` or some such).

If any argument has the wrong type, a ``TypeCheckError`` exception will be raised
at run time.
Class types, collection types, fixed-length collections and
type predicates can be annotated as well.

As of Python 3.5, PEP 484 specifies that annotations should be types and
their normal use will be type checking.
Many advanced types (such as ``Sequence[int]``) can now be defined via the
``typing`` module, which is also available at PyPI for earlier versions of
Python 3.

The present module supports these ``typing`` annotations, but it predates
Python 3.5 and therefore has other forms of type specification (via type
predicates) as well.
Many of these are equivalent, but some are more powerful.

Here is a more complex example:

::

  import typecheck as tc

  @tc.typecheck
  def foo2(record:(int,int,bool), rgb:tc.re("^[rgb]$")) -> tc.any(int,float) :
      # don't expect the following to make much sense:
      a = record[0]; b = record[1]
      return a/b if (a/b == float(a)/b) else float(a)/b

  foo2((4,10,True), "r")   # OK
  foo2([4,10,True], "g")   # OK: list is acceptable in place of tuple
  foo2((4,10,1), "rg")     # Wrong: 1 is not a bool, string is too long
  foo2(None,     "R")      # Wrong: None is no tuple, string has illegal character

These annotations mean that ``record`` is a 3-tuple of two ints and
an actual bool and ``rgb`` is a one-character string that is
either "r" or "g" or "b" by virtue of a regular expression test.
The result will be a number that can be either int or float.

The first and third of these are expressible with ``typing`` annotations as
well, the second is not. The closest approximation would look like this:

::

  import typing as tg
  import typecheck as tc

  @tc.typecheck
  def foo2(record:tg.Tuple[int,int,bool], rgb:str) -> tg.Union[int,float] :
      """rgb must be one of "r","g","b"."""
      a = record[0]; b = record[1]
      return a/b if (a/b == float(a)/b) else float(a)/b

  foo2((4,10,True), "r")   # OK
  foo2([4,10,True], "g")   # OK: list is acceptable in place of tuple
  foo2((4,10,1), "rg")     # Wrong: 1 is not a bool (but meant-to-be-too-long string is not detected)
  foo2(None,     "R")      # Wrong: None is no tuple (but meant-to-be-illegal character is not detected)



Other kinds of annotations:

- ``tc.optional(int)`` or ``tg.Optional[int]`` will allow int and None,
- ``tc.enum(1, 2.0, "three")`` allows to define ad-hoc enumeration types,
- ``tc.map_of(str, tc.list_of(Person))`` or
  ``tg.Mapping[str, tg.MutableSequence[Person]]``
  describe dictionaries or other mappings where all
  keys are strings and all values are homogeneous lists of Persons,
- and so on.

Tox-tested on CPython 3.3, 3.4, 3.5.

Find the documentation at
https://github.com/prechelt/typecheck-decorator