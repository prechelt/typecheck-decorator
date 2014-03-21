A decorator for functions, ``@typecheck``, to be used together with
Python3 annotations on function parameters and function results.
The decorator will perform dynamic argument type checking for every call to the function.

::

  @typecheck
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

The ``@typecheck`` decorator gives the above annotations the following meaning:
``foo1``'s argument ``a`` must have type ``int``,
``b`` has no annotation and can have any type whatsoever, it will not be checked,
``c`` must have type string,
and the function's result must be either
``True`` (not ``17`` or ``"yes"`` or ``[3,7,44]`` or some such) or
``False`` (not ``0`` or ``None`` or ``[]`` or some such).

If any argument has the wrong type, a ``TypeCheckError`` exception will be raised.
Class types, collection types, fixed-length collections and
type predicates can be annotated as well.
Here is a more complex example:

::

  from typecheck import typecheck
  import typecheck as tc

  @typecheck
  def foo2(record:(int,int,bool), rgb:tc.matches("^[rgb]$")) -> tc.any(int,float) :
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

Other kinds of annotations:

- ``tc.optional(int)`` will allow int and None,
- ``tc.enum(1, 2.0, "three")`` allows to define ad-hoc enumeration types,
- ``tc.dict_of(str, tc.list_of(Person))`` describes dictionaries where all
  keys are strings and all values are homogeneous lists of Persons,
- and so on.

Find the documentation at
https://github.com/prechelt/typecheck-decorator