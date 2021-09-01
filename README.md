typecheck-decorator
===================
Lutz Prechelt, 2014-2016, for Version 1.3

A decorator for functions, `@tc.typecheck`, to be used together with
Python3 annotations on function parameters and function results.
The decorator will perform dynamic argument type checking for every call to the function.

1 Introduction: A quick example
===============================

  ```Python
  @tc.typecheck
  def foo1(a:int, b=None, c:str="mydefault") -> bool :
      print(a, b, c)
      return b is not None and a != b
  ```

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
``False`` (not ``0`` or ``None`` or ``[]`` or some such) --
unless you've done unspeakable things and made Python believe in
other than those two time-tested boolean values.

Given these annotations, the arguments supplied in any call to ``foo1``
will (roughly speaking) be evaluated with the ``type()`` function and
the result compared to the annotated type.

If any argument has the wrong type, a ``TypeCheckError`` exception will be raised.
Class types and collection types can be annotated as well, but that
is *by far* not the end of the story, because in this package a "type"
can be any constraint on the set of allowable values.


2 Import style, usage style
===========================

For clarity, the recommended import style is as follows:

  ```Python
  import typing as tg
  import typecheck as tc
  ```

The remainder of this document will assume this import style.
(Beware of ``from typecheck import *`` , as there are functions any() and all() 
that are likely to break your code then.)

As for usage style, the idea of this package is not to approximate
static type checking.
Rather, you should use ``@tc.typecheck`` where appropriate ("gradual typing").
Good examples for such situations might be:
- You want to clarify your own thinking at module design time.
- Some callers of your package tend to be careless or ignorant
  and you want to make their contract violations explicit to reduce
  hassle.
- You want to safeguard against mistakes when modifying legacy code,
  so you add some typechecks first.
- You want to record the results of heroic reverse-engineering
  of legacy code.
- You want to minimize non-code documentation.

Some of your functions and methods will have annotations, many others will not.
And even for decorated functions and methods, only a subset of their
parameters may be annotated. Where appropriate.


3 How it works
==============

At function definition time, the ``@tc.typecheck`` decorator converts
each annotation into a predicate function (called a ``Checker``)
and stores all of these in the wrapper function.

At function execution time, the wrapper will
take each argument supplied to the function call,
submit it to its corresponding Checker predicate (if that exists),
and raise an exception if the Checker returns False.
The original function will be called then and its result
checked likewise if a result annotation had been provided.


4 The five sorts of annotation
==============================

``@tc.typecheck`` allows four different kinds of annotation to
some parameter PAR:
- **Types.**
  The annotation is an expression returning a type, typically
  just the name of a type.
- **Predicates.** The annotation is a function that turns the argument
  into True (for an acceptable argument)
  or False (for all others).
  (Remember that a predicate is a function, not a function call -- but it may
  be the result of a function call.)
- **Tuples** and **Lists.**
  The annotation is a tuple or list (rather than a type or a predicate)
  as explained below.
- **Dictionaries.**
  The annotation is a dictionary (rather than a type or a predicate)
  as explained below.
- **``typing`` annotations.**
  The annotation is one of those defined in the module ``typing``.
  (This module was introduced in Python 3.5 and is available from 
   PyPI for earlier Python 3 versions. 
   We will subsequently often call it ``tg``.)
  This is a special case of 'Types' introduced above. 
  It requires special handling internally and provides extended possibilities
  externally (e.g. describing generic functions or specifying container
  types with particular content types in a manner possibly understood by 
  static type checking tools).
  These are expected to become the standard over time because more tools
  and more programmers will readily understand them than the proprietary
  annotations.

The following subsections explain each of these annotation types.
The same annotations are valid for function results (as opposed to parameters)
as well.


4.1 Types as annotations
------------------------

The annotation is an expression for which ``inspect.isclass`` evaluates to True,
but which is not from the ``tg`` module.

Example:

   ```Python
   @tc.typecheck
   def foo2(a:int, d:dict, l:list=None) -> datetime.datetime :
     pass
   ```

Instead of a type name, this could of course also be
a function call returning a type
or the name of a variable that holds a type.
Such function calls will occur only once at function definition time.
(Static type checkers may not understand them.)

Meaning:
If the annotation declares type ``T``, the argument ``x`` must fulfil
``isinstance(x, T)``, so objects from subclasses of T are acceptable as well.
This same rule, that subclasses are also acceptable, holds for the other
annotation types as well.


4.2 Predicates as annotations
-----------------------------

The annotation evaluates to a function (or in fact any callable)
that will be called with the argument ``x`` supplied for parameter PAR
as its only argument and must return a value that evaluates to
  ``True`` (for an acceptable argument ``x``)
  or ``False`` (for all other ``x``).

Example:

   ```Python
   def is_even(n): return type(n) is int and n%2 == 0

   @tc.typecheck
   def foo3(a:int) -> is_even :
     return 2*a
   ```

You can define your own predicate as shown above or use one of the
predicate generators supplied with the package to create
a predicate on the fly.
(Static type checkers will usually not understand predicates.)


4.3 Tuples and lists as annotations
-----------------------------------

The annotation is an expression that evaluates to a tuple or list
(rather than a type or a predicate);
more precisely, it can be any ``collections.abc.Sequence`` object.
This is a very pragmatic extension for programs that do not model
every little data structure as a class
but rather make heavy use of the built-in sequence types.
(Static type checkers will usually not understand such annotations.)

This is easiest explained by examples:

   ```Python
   @tc.typecheck
   def foo4(pair:(int,int), descriptor:[int, float, float, bool]):
     pass
   foo4((1,2), [3, 2.0, 77.0, True])    # OK
   foo4([1,2], [3, 2.0, 77.0, True])    # OK: list is acceptable as tuple
   foo4((1,2), (3, 2.0, 77.0, True))    # Wrong: descriptor must be list
   foo4((1,2,3), [3, 2.0, 77.0, True])  # Wrong: pair too long
   foo4((0.0,2), [3, 2.0, 77.0, True])  # Wrong: pair[0] type mismatch
   foo4((1,2), None)                    # Wrong: descriptor is missing

   @tc.typecheck
   def foo5(pair:(int,int), descriptor:[int, (float, float), bool]):
     pass
   foo5((1,2), [3, (2.0, 77.0), True])  # OK
   foo5([1,2], [3, 2.0, 77.0, True])    # Wrong: descriptor[1] type mismatch
   ```

General meaning:
- The annotation is a sequence of length N.
  Its entries could themselves each serve as an annotation.
- The annotation will match only an argument of exactly length N.
- The argument's i-th element must fulfil the condition implied by
  the annotation's i-th element.
- If the annotation is a list, the argument must be a list (or list subclass) object.
- If it is a tuple, the argument can be a tuple, tuple subclass object,
  list, or list subclass object.
- If it is a subclass S of list or tuple, the same rules apply,
  except only S and its subclasses are acceptable and
  the plain-tuple-can-be-list special case does no longer apply.

``collections.namedtuple`` classes produce tuple objects, so you can pass
named tuples as arguments for methods having Sequence annotations without 
problem.
Do not use a named tuple for an annotation, though, because its names
will be ignored, which is confusing and error-prone.
(You can use a namedtuple type as an annotation without problems.)


4.4 Dictionaries as annotations
-------------------------------

The annotation is an expression that evaluates to a dictionary
(rather than a type or a predicate);
more precisely, it can be any ``collections.abc.Mapping`` object.
Again, this is a pragmatic extension for programs that do not model
every little data structure as a class
but rather make heavy use of the built-in types.
The annotation prescribes a fixed set of keys and a type for
the value of each key. All keys must be present.
(Static type checkers will usually not understand such annotations.)

Examples:

   ```Python
   @tc.typecheck
   def foo6(point:dict(x=int,y=int)):
     pass
   foo6(dict(x=1, y=2))         # OK
   foo6({"x":1, "y":2})         # OK
   foo6(collections.UserDict(x=1, y=2))  # OK
   foo6(dict(x=1))              # Wrong: key y is missing
   foo6(dict(x=1, y="huh?"))    # Wrong: type error for y
   foo6(dict(x=1, y=2, z=10))   # Wrong: key z is not allowed
   ```


4.5 ``typing`` annotations
--------------------------

After the typecheck-decorator package had existed for a while,
Python 3.5 standardized a notation for type annotations via the
new module ``typing``.
That notation is supported here as well.
If you do use an older version than Python 3.5, get the ``typing`` module
from PyPI.

If you only use typecheck-decorator, you can freely mix these new
notation with the older notations described above.
If you also want to apply other tools with your typechecking annotations
(e.g. tools for static typechecking),
those will be more helpful if you restrict yourself to the notations 
described in Sections 4.1 and 4.5 only.

Examples:

   ```Python
   import typing as tg
   @tc.typecheck
   def foo7(point: tg.Tuple[int, int]):
     pass
   foo7((4, 2))         # OK
   foo7(None)           # Wrong, must use tg.Optional[tg.Tuple[int,int]]
   foo7((4, 2, 0))      # Wrong
   foo7((4, 2.0))       # Wrong
   foo7((4, None))      # Wrong
   ```

See the following places for documentation and examples of the possibilities:
- The API documentation of the ``typing`` module.
- PEP 484
- the file tc.test_tg_annotations.py
However, so far the implementation of this support is not yet complete;
see Section "Limitations" for the remaining gaps.
If you have been using ``tc`` for a while already or if you prefer
its proprietary notation over that of ``tg``, be aware that there is one
feature in ``tg`` that is more powerful than previously available in ``tc``: 
``tg.TypeVar`` (type variables).
It is presumably (I have not tested this much, so there may be gaps)
possible to mix standard ``tg`` and proprietary ``tg`` style annotations 
freely, including type variables.


5 Predicate generators
======================

Annotating type names (other than those from ``tg``) and 
fixed-length tuples does not get you very far,
because
- such an annotation will not accept ``None``;
- wherever you use duck typing, your "type" is defined by a set
  of signatures rather than a fixed name;
- you often would like to check for things such as "a list of strings"
  for arbitrary-length lists.

So you will frequently need to use a predicate to do your checking.
Implementing these each time would be cumbersome, so this package
comes along with a good basic library of such things.
To be useful, these "things" actually have to be predicate generators:
Higher-order functions that return a predicate when called.
But do not worry, their use looks perfectly straightforward eventually.


5.1 Built-in predicate generators
---------------------------------

One of these, ``optional``, you will surely need;
all others are a bit more specialized.
As any annotation, all of them can be used for parameters and results alike.
Here we go:

**tc.optional(annot)**:

Takes any other annotation ``annot``.
Allows all arguments that ``annot`` allows, plus ``None``:

   ```Python
   @tc.typecheck
   def foo(a:int):
     pass
   @tc.typecheck
   def foo_opt(a:tc.optional(int)):
     pass
   foo(123)       # OK
   foo_opt(123)   # OK
   foo(None)      # Wrong: None does not have type int
   foo_opt(None)  # OK
   ```
An equivalent alternative is ``tg.Optional[annot]``.

**tc.hasattrs(*names)**:

Type-checked duck-typing:
Takes a variable number of strings containing attribute names.
Allows all arguments that possess every one of those attributes.

   ```Python
   class FakeIO:
       def write(self):  pass
       def flush(self):  pass
   @tc.typecheck
   def foo_re(a: tc.hasattrs("write", "flush")):  pass

   foo(FakeIO())       # OK
   del FakeIO.flush
   foo(FakeIO())       # Wrong, because flush attribute is now missing
   ```

**tc.re(regexp)**:

Takes a string containing a regular expression.
Allows all arguments that are strings and contain (as per ``re.search``)
what is described by that regular expression.
Also works for bytestrings if you use a bytestring regular expression.

   ```Python
   @tc.typecheck
   def foo(hexnumber: tc.re("^[0-9A-F]+$")) -> tc.re("^[0-9]+$"):
       return "".join(reversed(k))

   foo("1234")        # OK
   foo("12AB")        # Wrong: argument OK, but result not allowed
   ```

**tc.seq_of(annot, checkonly=4)**:

Takes any other annotation ``annot``.
Allows any argument that is a sequence
(tuple or list, in fact any ``collections.abc.Sequence``)
in which each element is allowed by ``annot``.
Not all violations will be detected because, for efficiency reasons,
the check will cover only a sample of ``checkonly`` elements of the sequence.
This sample always includes the first and last element, the rest
is a random sample.
As an interesting special case, consider submitting a string to a
parameter declared as ``tc.seq_of(str)``. A string is a sequence.
Its elements are strings. So the call should be considered OK.
Since this is usually not what you want, ``tc.seq_of()`` will 
always reject a string argument in order to avoid a confusing type
of mistake.

   ```Python
   @tc.typecheck
   def foo_so(s: tc.seq_of(str)):  pass

   foo_so(["a", "b"])         # OK
   foo_so(("a", "b"))         # OK, a tuple
   foo_so([])                 # OK
   foo_so(["a"])              # OK
   foo_so("a")                # Wrong: not a sequence in seq_of sense
   foo_so(["a", 1])           # Wrong: inhomogeneous
   almost_ok = 1000*["a"] + [666]
   foo_so(almost_ok)          # Wrong: inhomogeneous, will fail
   almost_ok += ["a"]
   foo_so(almost_ok)          # Wrong, but will fail only 0.25% of the time
   ```
An equivalent alternative with fixed ``checkonly``
is ``tg.Sequence[annot]``.

**tc.list_of(annot, checkonly=4)**:

Just like ``seq_of(annot, checkonly)``, except that it requires the
sequence to be a ``collections.abc.MutableSequence``.

   ```Python
   @tc.typecheck
   def foo_lo(s: tc.list_of(str)):  pass

   foo_so(["a", "b"])         # OK
   foo_so(("a", "b"))         # Wrong: a tuple is not a MutableSequence
   ```
An equivalent alternative with fixed ``checkonly``
is ``tg.MutableSequence[annot]``.

**tc.map_of(keys_annot, values_annot, checkonly=4)**:

Takes two annotations ``keys_annot`` and ``values_annot``.
Allows any argument that is a ``collections.abc.Mapping`` (typically a dict)
in which each key is allowed by keys_annot and
each value is allowed by values_annot.
Not all violations will be detected because for efficiency reasons,
the check will cover only the first ``checkonly`` pairs returned by the
mapping's iterator.
In contrast to ``tc.seq_of``, this sample is not a variable random sample.

   ```Python
   @tc.typecheck
   def foo_do(map: tc.map_of(int, str)) -> tc.map_of(str, int):
       return { v: k  for k,v in x.items() }

   assert foo({1: "one", 2: "two"}) == {"one": 1, "two": 2}  # OK
   foo({})             # OK: an empty dict is still a dict
   foo(None)           # Wrong: None is not a dict
   foo({"1": "2"})     # Wrong: violates values_annot of arg and keys_annot of result
   ```
An equivalent alternative with fixed ``checkonly``
is ``tg.Mapping[annot]``.

**tc.enum(*values)**:

Takes any number of arguments.
Allows any argument that is equal to any one of them
(as opposed to being an instance of one).
Effectively defines an arbitrary, ad-hoc enumeration type.

   ```Python
   @tc.typecheck
   def foo_ev(arg: tc.enum(1, 2.0, "three", [1]*4)): pass

   foo_ev(1)     # OK
   foo_ev(2*1.0) # OK
   foo_ev("thr"+2*"e")  # OK
   foo_ev([1,1,1,1])    # OK
   foo_ev(1.0)   # OK, because 1.0 == 1
   foo_ev("thr") # Wrong: not in values list
   foo_ev([1,1]) # Wrong: not in values list
   ```


**tc.range(low, high)**:

Takes two limit values low and high that must both have
the same type (typically int or float). Will allow all arguments
having that same type and lying between (including) low and high.
The type needs not be numeric: any type supporting
__le__ and __ge__ with range semantics will do.

   ```Python
   @tc.typecheck
   def foo(arg: tc.range(0.0, 100.0)): pass

   foo(0.0)    # OK
   foo(8.4e-3) # OK
   foo(100.0)  # OK
   foo(1)      # Wrong: not a float
   foo(111.0)  # Wrong: value too large
   ```


**tc.any(*annots)**:

Takes any number of arguments, each being a valid annotation.
Allows any argument that is allowed by any one of those annotations.
Effectively defines an arbitrary union type.
You could think of it as an n-ary ``or``.

   ```Python
   @tc.typecheck
   def foo_any(arg: tc.any(int, float, tc.matches("^[0-9]+$")): pass

   foo_any(1)     # OK
   foo_any(2.0)   # OK
   foo_any("3")   # OK
   foo_any("4.0") # Wrong: not allowed by any of the three partial types
   ```
An equivalent alternative is ``tg.Union[*annots]``.

**tc.all(*annots)**:

Takes any number of arguments, each being a valid annotation.
Allows any argument that is allowed by every one of those annotations.
Effectively defines an arbitrary intersection type.
You could think of it as an n-ary ``and``.

   ```Python
   def complete_blocks(arg):
       return len(arg) % 512 == 0

   @tc.typecheck
   def foo_all(arg: tc.all(tc.any(bytes,bytearray), complete_blocks)): pass

   foo_all(b"x" * 512)              # OK
   foo_all(bytearray(b"x" * 1024))  # OK
   foo_all("x" * 512)      # Wrong: not a bytearray or bytes
   foo_all(b"x" * 1012)    # Wrong: no complete blocks
   ```

**tc.none(*annots)**:

Takes any number of arguments, each being a valid annotation.
Allows any argument that is allowed by no single one of those annotations.
Effectively defines a type taboo.
You could think of it as "not any" or as "all not".

   ```Python
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

   no_tests_please("stuff")        # OK
   no_tests_please(TestCase())     # Wrong: not wanted here
   no_tests_please(MyCheckers())   # Wrong: superclass not wanted here
   no_tests_please(AddressTest())  # Wrong: suspicious class name
   ```


5.2 Built-in fixed predicates
-----------------------------

Note that these must be used without parentheses: You need to submit
the function, not call it.

**tc.anything**:

This is the null typecheck: Will accept any value whatsoever, including None.
The meaning is effectively the same as attaching no annotation at all,
but explicitly declaring that no restrictions are intended may be
desirable for pythonic clarity.
Note: This is equivalent to ``tc.all()``, that is, all-of-nothing,
and also equivalent to ``tc.none()``, that is, none-of-nothing,
but is much clearer.

   ```Python
   @tc.typecheck
   def foo_any(arg: tc.anything) --> tc.anything:
       pass

   foo_any(None)             # OK
   foo_any([[[[{"one":True}]]]]])  # OK
   foo_any(foo_any)          # OK
   ```
An equivalent alternative is ``tg.Any``.


**callable**

The Python builtin predicate ``callable()`` is also useful
as a typechecking predicate.

   ```Python
   @tc.typecheck
   def foo_callable(func: callable, msg: str):
       func(msg)

   foo_callable(print)      # OK
   foo_callable(open)       # OK
   foo_callable("print")    # Wrong
   ```
Once supported (so far it is not), a much more powerful alternative 
for callables with fixed signatures will be
``tg.Callable[[*argtype_annots], returntype_annot]``.


5.3 Custom predicate generators
-------------------------------

If the above library of generators is insufficient for your needs,
just write the missing ones yourself:
A predicate generator is simply a function that returns an
anonymous function with effectively the following signature:

  ```Python
  def mypredicate(the_argument: tc.anything) -> bool
  ```

No extension API is required.

Here is an example:

   ```Python
   # defining a custom predicate generator:
   def blocks(blocksize: int) -> bool :
      def bytes_with_blocksize(arg):
         """ensures the arg is a bytearray with the given block size"""
         return (isinstance(arg, bytes) or isinstance(arg, bytearray)) and
                len(arg) % blocksize == 0
      return bytes_with_blocksize

   # using the custom predicate generator:
   @tc.typecheck
   def transfer(mydata: blocks(512)):  pass
   ```


6 Exceptions
============

- If an argument does not fulfil the corresponding parameter annotation,
  a ``tc.InputParameterError`` will be raised.

- If a function result does not fulfil the corresponding annotation,
  a ``tc.ReturnValueError`` will be raised.

- Both of these are subclasses of  ``tc.TypeCheckError``.

- If an annotation is used that does not fit into the categories
  described above, a ``tc.TypeCheckSpecificationError`` will be raised
  at function definition time.


7 Efficiency considerations
===========================

@tc.typecheck may appear to be expensive in terms of runtime,
but actually Python is doing shiploads of similar things
all the time.

There are essentially two cases where execution time will
become a real issue:
- An annotation on a trivial function that is being
  called frequently in a tight loop.
- Checking the types of every element of a large data structure,
  when only few of those elements will actually be accessed.


Limitations
===========

- There is currently no support for 
  - ``tg.Callable`` (*)
  - ``tg.io`` (*)
  - ``tg.re`` (*)
  - decorator ``@tg.no_type_check``
  - PEP 484 "type comments"
  For those marked (*), support will follow in a future version.
- Python 3 has no unbound methods anymore, therefore
  binding of type variables to instances of a generic class ``C``
  will only be recognized heuristically: The first parameter of 
  each method ``m`` involved must be named ``self`` and
  the first argument of stand-alone functions must not be named ``self``.
- Type variables can only be bound to types, not to type checking predicates.
- Type variables follow an "observed common supertype" semantics.
  This means that when a type variable is checked against several different 
  types over time, it will bind to the type first seen, then accept that
  type as well as its subclasses, and will later rebind if checked against
  a superclass. It will reject only values that are neither subclass nor
  superclass values of the current binding 
  (but bounds and constraints are obeyed).
  This is the most sensible semantics I could think of, but may _appear_ overly
  liberal in some situations.
- There is a bug in the combination of at least Python 3.4 with
  PyPI typing 3.5.0.1 that makes e.g. ``issubclass(tg.Iterable, tg.Generic)``
  false (on the other hand, ``issubclass(tg.Sequence, tg.Iterable)`` is true
  as it should). 
  The full implications for type checking Generics are unclear,
  expect some Generics type checks to _perhaps_ go wrong in this configuration.
- The contents of ``tg.Generic`` containers are checked only in the following
  cases:
  - subtypes of ``tg.Sequence`` with exactly 1 generic parameter:
    will check the first element, last element, and two random elements.
  - subtypes of ``tg.Mapping`` with exactly 2 generic parameters:
    will check the first four pairs returned by ``items()``.
  - other subtypes of ``tg.Iterable``:
    will check the first four elements.
- Complex ``tg.Generic`` cases can sometimes not be content-checked, 
  because ``tg`` currently has no mechanism for
  determining the meaning of the type variables involved.
  For instance, ``tg.ItemsView`` has three generic parameters 
  ``(tg.T_co, tg.KT, tg.VT_co)``, the first of which represents the
  ``tg.Tuple[tg.KT, tg.VT_co]`` returned by each call to the iterator -- but
  how, in general (that is, for user-defined types), is a poor type checker
  to know this?
- Contrary to PEP 484, a default argument value of ``None``
  does not yet modify type ``X`` to become ``tg.Optional[X]``
  (although using ``tg.get_type_hints()`` for the implementation would 
  purportedly make that easy).
- PEP 484 forward references must so far use simple names 
  (such as ``'MyClass'``),
  not qualified ones (such as ``'mymodule.MyClass'``).
  The class thus referenced may live wherever it pleases.
  The forward reference string needs not be evaluable at the point
  of the checked function call.
  Types are checked by name comparison, not by evaluation.
  This means an argument of the wrong type will pass the check if 
  that wrong type has the same base name as the intended type.
  Support for qualified names may or may not be added in a future version.
  Checking by evaluation may or may not be added in a future version.
- This module does not follow Section "The numeric tower"
  of PEP 484, which suggests to accept ``int`` where ``float``
  is annotated. For us, these two are (so far) considered
  incompatible and you will need to annotate ``numbers.Float`` if
  you want it mix them.
- Likewise, ``bytearray`` and ``memoryview`` are not currently
  acceptable where ``bytes`` is declared; you currently need to
  use ``tg.ByteString`` to mix those.
- PEP 484 ``tg.cast`` does currently not check anything. 
   (As long as the claim formulated by the cast
   is correct, this is sufficient.)
- The module does not read PEP 484 stub files.
   (Typechecking large parts of in particular the builtins
    would create performance problems anyway.)
- The module does not support the ``@overload`` decorator.
  If ``@overload`` is used, only the last declaration executed for a name 
  survives, whether it is decorated or not.
- The proprietary annotations described in Sections 4.2, 4.3, and 4.4
  of the present document
  do not currently conform to PEP 484, because they result in functions
  rather than types; see "What about existing uses of annotations?" in PEP 484.
  If you are not interested in static type checking, you can use them anyway.
  A future version will likely convert them such that they result in types.
- The ``@tc.typecheck`` decorator will effectively modify the Python-visible
  signature of the decorated function:
  Essentially, the resulting signature is always ``(*args, **kwargs)``.
  This will perhaps one day be changed by using the
  ``decorator`` package or a similar technique.
- The exception messages should be more specific, e.g. for sequences and dicts
  and in particular where type variable violations are involved.



Version history
===============

- **0.1b**: 2012, Original version ``typecheck3000.py`` by
  Dmitry Dvoinikov <dmitry@targeted.org>. See
  http://www.targeted.org/python/recipes/typecheck3000.py

- **0.2b**: 2014-03-20, prepared by Lutz Prechelt.
  - Added documentation.
  - Fixed a number of errors in the tests that did not foresee
    that annotations will be checked in a random order.
  - Added ``setup.py``.
  - Replaced the not fully thought-through interpretation of iterables
    by a more specialized handling of tuples and lists.
  - Renamed several of the predicate generators.
  First version that was packaged and uploaded to PyPI.
  **Expect the API to change!**

- **0.3b**: 2014-03-21
  - Renamed either_value to enum
  - Renamed either_type to any
  - Renamed matches to has and made it use re.search, not re.match
  - Introduced all and none
  - Introduced a post-installation self-test, because I am not yet
    sure whether it will work on other platforms and with other Python versions
  Feedback is welcome!

- **1.0**: 2015-01-28
  - removed tuple_of
  - renamed sequence_of to seq_of and generalized it to collections.Sequence
  - added special case: a str will no longer be considered a seq_of(str)
  - generalized list_of to collections.Sequence
  - renamed dict_of to map_of and generalized it to collections.Mapping
  - renamed regexp matching from 'has' to 're'
  - added checkonly limit to seq_of, list_of, and map_of
  - added Mapping annotations (analogous to Sequence annotations)
  - added range
  - provided the predicates with appropriate __name__ attributes
  
- **1.1**:
  - various small improvements to the documentation

- **1.2**:
  - FIX: added checking for non-kwonlyargs named arguments
  - cut the implementation and tests into several pieces
  
- **1.3**:
  - introduces support for annotations according to the Python 3.5
    ``typing`` module; see Sections 4.5 and "Limitations"
  - an awkward exception rule has been dropped:
    you can no longer pass a ``collections.namedtuple`` value
    to an argument annotated with a fixed mapping.


Further contributors
====================

Benjamen Keroack <bkeroack@gmail.com> (v1.1: PyPy test fixes, seq_of(str) hint)
Andres Osorio <cosoriog@gmail.com> (v1.2: keyword args checking fix)


Similar packages
================

- ``typecheck3`` is based on the same original code of Dmitry Dvoinikov
  as typecheck-decorator,
  but (as of 0.1.0) lacks the tests, corrections, documentation,
  and API improvements available here.
- ``gradual`` has a similar overall approach of using a decorator and annotations.
  Compared to gradual, typecheck-decorator uses a more pragmatic approach and
  is far more flexible in expressing types.
  gradual as of 2015-12 has status "pre-alpha".
- ``threecheck`` is similar to typecheck-decorator in
  approach and expressiveness, except it has (as of v1.0)
  no support for the ``typing`` module.
