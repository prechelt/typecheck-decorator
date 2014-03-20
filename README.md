typecheck-decorator
###################

Lutz Prechelt, 2014

A decorator for functions, `@typecheck`, to be used together with
Python3 annotations on function parameters and function results.
The decorator will perform dynamic argument type checking for every call to the function.

1 Introduction: A quick example
===============================

  ```Python
  @typecheck
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

The ``@typecheck`` decorator gives the above annotations the following meaning:
``foo1``'s argument ``a`` must have type ``int``,
``b`` can have any type whatsoever, it will not be checked,
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

The recommended import style is as follows:

  ```Python
  from typecheck import typecheck    # for the decorator
  import typecheck as tc             # for clarity for all other objects
  ```

As for usage style, the idea of this package is not to approximate
static type checking.
Rather, you should use ``@typecheck`` "where appropriate".
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

Some functions and methods will have annotations, many others will not.
And even for decorated functions and methods, only a subset of their
parameters may be annotated. Where appropriate.


3 How it works
==============

At function definition time, the ``@typecheck`` decorator converts
each annotation into a predicate function (called a ``Checker``)
and stores all of these in the wrapper function.

At function execution time, the wrapper will
take each argument supplied to the function call,
submit it to its corresponding Checker predicate (if that exists),
and raise an exception if the Checker returns False.
The original function will be called then and its result
checked likewise if a result annotation had been provided.


4 The three sorts of annotation
===============================

``@typecheck`` allows three different kinds of annotation to
some parameter PAR:
- **Types.**
  The annotation is an expression returning a type, typically
  just the name of a type.
- **Predicates.** The annotation is a function that turns the argument
  into True (for an acceptable argument)
  or False (for all others).
  Note that a predicate is a function, not a function call.
- **Tuples** and **Lists.**
  The annotation is a tuple or list (rather than a type or a predicate)
  as explained below.

The following subsections explain each of these.


4.1 Types as annotations
------------------------

The annotation is an expression for which ``inspect.isclass`` evaluates to True.

Example:

   ```Python
   @typecheck
   def foo2(a:int, d:dict, l:list=None) -> datetime.datetime :
     pass
   ```

Instead of a type name, this could of course also be
a function call returning a type
or the name of a variable that holds a type.

Meaning:
If the annotation declares type ``T``, the argument ``x`` must fulfil
``isinstance(x, T)``, so objects from subclasses of T are acceptable as well.


4.2 Predicates as annotations
-----------------------------

The annotation evaluates to a function (or in fact any callable)
that will be called with the argument ``x`` supplied for parameter PAR
as its only argument and must return a value that evaluates to
  True (for an acceptable argument ``x``)
  or False (for all other ``x``).

Example:

   ```Python
   def is_even(n): type(n) is int and n%2 == 0

   @typecheck
   def foo3(a:int) -> is_even :
     return 2*a
   ```

You can define your own predicate as shown above or use one of the
predicate generators supplied with the package to create
a predicate on the fly.


4.3 Tuples and lists as annotations
-----------------------------------

The annotation is an expression that evaluates to a tuple or list
(rather than a type or a predicate).
This is a very pragmatic extension for programs that do not model
every little data structure as a class
but rather make heavy use of the built-in sequence types.

It is easiest explained by examples:

   ```Python
   @typecheck
   def foo4(pair:(int,int), descriptor:[int, float, float, bool]):
     pass
   foo4((1,2), [3, 2.0, 77.0, True])    # OK
   foo4([1,2], [3, 2.0, 77.0, True])    # OK: list is acceptable as tuple
   foo4((1,2), (3, 2.0, 77.0, True))    # Wrong: descriptor must be list
   foo4((1,2,3), [3, 2.0, 77.0, True])  # Wrong: pair too long
   foo4((0.0,2), [3, 2.0, 77.0, True])  # Wrong: pair[0] type mismatch
   foo4((1,2), None)                    # Wrong: descriptor is missing

   @typecheck
   def foo5(pair:(int,int), descriptor:[int, (float, float), bool]):
     pass
   foo5((1,2), [3, (2.0, 77.0), True])  # OK
   foo5([1,2], [3, 2.0, 77.0, True])    # Wrong: descriptor[1] type mismatch
   ```

General meaning:
- The annotation is a sequence of length N.
  Its entries could themselves serve as annotations.
- If it is a list, the argument must be a list (or list subclass) object.
- If it is a tuple, the argument can be a tuple, tuple subclass object,
  list, or list subclass object.
- If it is a subclass S of list or tuple, the same rules apply,
  except only S and its subclasses are acceptable and
  the plain-tuple-can-be-list special case does no longer apply.
- The annotation will match only an argument of exactly length N.
- The argument's i-th element must fulfil the condition implied by
  the annotation's i-th element.


5 Predicate generators
======================

Annotating type names and fixed-length tuples does not get you very far,
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

One of these, ``optional``, you will surely need;
all others are a bit more specialized.
Here we go:


   ```Python
   @typecheck
   def foo_o1(a:int):
     pass

   @typecheck
   def foo_o1(a:int):
     pass
   foo4((1,2), [3, 2.0, 77.0, True])    # OK

!!!


6 Exceptions
============

- If an argument does not fulfil the corresponding parameter annotation,
  a ``tc.InputParameterError`` will be raised.

- If a function result does not fulfil the corresponding annotation,
  a ``tc.ReturnValueError`` will be raised.

- Both of these are subclasses of  ``tc.TypeCheckError``.

- If an annotation is used that does not fit into the categories
  described above, a ``tc.TypeCheckSpecificationError`` will be raised.


7 Efficiency considerations
===========================

@typecheck may appear to be expensive in terms of runtime,
but actually Python is doing shiploads of similar things
all the time.

There are essentially only two cases where execution time might
become a real issue:
- A non-trivial annotation on a trivial function that is being
  called very frequently in a tight loop.
- You check the types of all elements of a large data structure
  many times, but most often they will not actually be accessed.


Limitations
===========

1. The decorated function will have a different signature:
   Essentially, it is always ``(*args, **kwargs)``.
   This will hopefully one day be changed by using the
   ``decorator`` package or a similar technique.
1. There should be a way to specify fixed dictionaries or named tuples
   like one can specify fixed lists or tuples.
   This feature will also some day appear, weather permitting.


Version history
===============

- **0.1b**: Original version ``typecheck3000.py`` by
  Dmitry Dvoinikov <dmitry@targeted.org>. See
  http://www.targeted.org/python/recipes/typecheck3000.py

- **0.2b**:
  First version to be packaged and uploaded to PyPI.
  - Added documentation.
  - Fixed a number of errors in the tests that did not foresee
    that annotations will be checked in a random order.
  - Added ``setup.py`` with on-installation auto-testing.
  - Replaced the not fully thought-through interpretation of iterables
    by a more specialized handling of tuples and lists.
  - Renamed several of the predicate generators.


TO DO
=====

- use decorator package.
  Unfortunately, as of 3.4.0 (2014-03-20) this does not claim
  to the Python3-compatible...
- add predicate generator for fixed-structure dict and namedtuple
- replace ``disable()`` by
  ``mode(decorate=True, typecheck=True, collectioncheck_limit=False)``
- add more specialized exception messages, e.g. for sequences