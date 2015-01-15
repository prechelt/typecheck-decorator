typecheck-decorator
===================
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

The recommended import style is as follows:

  ```Python
  from typecheck import typecheck    # for the decorator
  import typecheck as tc             # for clarity for all other objects
  ```

The remainder of this document will assume these imports.

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

The following subsections explain each of them.
The same annotations are valid for results (as opposed to parameters) as well.


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

Abstract base classes defined in the *collections* module are supported for duck-typed parameters:

   ```Python
   import collections
   
   def DuckTypedList(collections.MutableSequence):
      def __getitem__(self, item):
          pass
      def __iter__(self):
          pass
      def __len__(self):
          pass
          
   @typecheck
   def foo(m: collections.MutableSequence):
       pass
   ```


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
   @typecheck
   def foo_o1(a:int):
    pass
   @typecheck
   def foo_o2(a:tc.optional(int)):
    pass
   foo_o1(123)    # OK
   foo_o2(123)    # OK
   foo_o1(None)   # Wrong: None does not have type int
   foo_o2(None)   # OK
   ```

**tc.hasattrs(*names)**:

Type-checked duck-typing:
Takes a variable number of strings containing attribute names.
Allows all arguments that possess every one of those attributes.

   ```Python
   class FakeIO:
       def write(self):  pass
       def flush(self):  pass
   @typecheck
   def foo_re(a: tc.hasattrs("write", "flush")):  pass

   foo(FakeIO())       # OK
   del FakeIO.flush
   foo(FakeIO())       # Wrong, because flush attribute is missing
   ```

**tc.has(regexp)**:

Takes a string containing a regular expression string.
Allows all arguments that are strings and contain what is described
by that regular expression (as defined by ``re.search``).
Also works for bytestrings if you use a bytestring regular expression.

   ```Python
   @typecheck
   def foo(hexnumber: tc.has("^[0-9A-F]+$")) -> tc.has("^[0-9]+$"):
       return "".join(reversed(k))

   foo("1234")        # OK
   foo("12AB")        # Wrong: argument OK, but result not allowed
   ```

**tc.seq_of(annot)**:

Takes any other annotation ``annot``.
Allows any argument that is a sequence (tuple, list, collections.Sequence) in which
each element is allowed by ``annot``.

*WARNING* - ``str`` satisfies collections.Sequence, meaning that a plain string will satisfy the following
predicate: ``tc.seq_of(str)`` since each subelement (character) is also string object. Use ``list_of`` if you
want to restrict to a list of strings (duck-typed or otherwise).

   ```Python
   
   class DuckTypedSequence(collections.Sequence):
      def __getitem__(self, item):
         pass
      def __len__(self):
         pass
   
   @typecheck
   def foo_so(s: tc.sequence_of(str)):  pass

   foo_so(["a", "b"])          # OK
   foo_so(("a", "b"))          # OK, a tuple
   foo_so([])                  # OK
   foo_so(["a"])               # OK
   foo_so(DuckTypedSequence()) # OK
   foo_so("a")                 # Wrong: not a sequence in sequence_of sense
   foo_so(["a", 1])            # Wrong: inhomogeneous
   ```

**tc.list_of(annot)**:

Takes any other annotation ``annot``.
Allows any argument that satisfies collections.MutableSequence (including built-in list) in which
each element is allowed by ``annot``

   ```Python
   
   class DuckTypedList(collections.MutableSequence):
      def __getitem__(self, item):
         pass
      def __setitem__(self, item, value):
         pass
      def __delitem__(self, item):
         pass
      def __len__(self):
         pass
      def insert(self, index, item):
         pass
         
   @typecheck
   def foo_so(s: tc.list_of(str)):  pass

   foo_so(["a", "b"])         # OK
   foo_so(("a", "b"))         # Wrong, not a list
   foo_so([])                 # OK
   foo_so(["a"])              # OK
   foo_so(DuckTypedList())    # OK
   foo_so("a")                # Wrong: not a sequence in list_of sense
   foo_so(["a", 1])           # Wrong: inhomogeneous
   ```

**tc.dict_of(keys_annot, values_annot)**:

Takes two annotations ``keys_annot`` and ``values_annot``.
Allows any argument that satisfies collections.Mapping (including built-in dict) in which
each key is allowed by keys_annot and
each value is allowed by values_annot.

   ```Python
   
   class DuckTypedDict(collections.Mapping):
      def __getitem__(self, item):
         pass
      def __iter__(self):
         pass
      def __len__(self):
         pass
         
   @typecheck
   def foo_do(map: tc.dict_of(int, str)) -> tc.dict_of(str, int):
       return { v: k  for k,v in x.items() }

   assert foo({1: "one", 2: "two"}) == {"one": 1, "two": 2}  # OK
   foo({})              # OK: an empty dict is still a dict
   foo(DuckTypedDict()) # OK: duck-typed dict is still a dict
   foo(None)            # Wrong: None is not a dict
   foo({"1": "2"})      # Wrong: violates values_annot of argument
                          (also violates keys_annot of result)
   ```

**tc.enum(*values)**:

Takes any number of arguments.
Allows any argument that is equal to any one of them
(as opposed to being an instance of one).
Effectively defines an arbitrary, ad-hoc enumeration type.

   ```Python
   @typecheck
   def foo_ev(arg: tc.enum(1, 2.0, "three", [1]*4)): pass

   foo_ev(1)     # OK
   foo_ev(1.0)   # Wrong: not in values list
   foo_ev([1,1,1,1])  # OK
   ```
   
**tc.any(*annots)**:

Takes any number of arguments, each being a valid annotation.
Allows any argument that is allowed by any one of those annotations.
Effectively defines an arbitrary union type.
You could think of it as an n-ary ``or``.

   ```Python
   @typecheck
   def foo_any(arg: tc.any(int, float, tc.matches("^[0-9]+$")): pass

   foo_any(1)     # OK
   foo_any(2.0)   # OK
   foo_any("3")   # OK
   foo_any("4.0") # Wrong: not allowed by any of the three partial types
   ```

**tc.all(*annots)**:

Takes any number of arguments, each being a valid annotation.
Allows any argument that is allowed by every one of those annotations.
Effectively defines an arbitrary intersection type.
You could think of it as an n-ary ``and``.

   ```Python
   def complete_blocks(arg):
       return len(arg) % 512 == 0

   @typecheck
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

   @typecheck
   def no_tests_please(arg: tc.none(TestCase, classname_contains_Test)): pass

   no_tests_please("stuff")        # OK
   no_tests_please(TestCase())     # Wrong: not wanted here
   no_tests_please(MyCheckers())   # Wrong: superclass not wanted here
   no_tests_please(AddressTest())  # Wrong: suspicious class name
   ```

**tc.anything**:

This is the null typecheck: Will accept any value whatsoever, including None.
The meaning is effectively the same as attaching no annotation at all,
but explicitly declaring that no restrictions are intended may be
desirable for pythonic clarity.
Note: This is equivalent to ``tc.all()``, that is, all-of-nothing,
and also equivalent to ``tc.none()``, that is, none-of-nothing,
but is much less confusing.

   ```Python
   @typecheck
   def foo_any(arg: tc.anything) --> tc.anything:
       pass

   foo_ev(None)             # OK
   foo_ev([[[[{"one":True}]]]]])  # OK
   foo_ev(foo_ev)           # OK
   ```


5.2 Custom predicate generators
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
   @typecheck
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
- Checking the types of every element of a large data structure
  many times, although only few of those elements will actually be accessed.


Limitations
===========

1. The decorated function will have a different signature:
   Essentially, it is always ``(*args, **kwargs)``.
   This will hopefully one day be changed by using the
   ``decorator`` package or a similar technique.
2. There should be a way to specify fixed dictionaries or named tuples
   like one can specify fixed lists or tuples.
   This feature will also some day appear, weather permitting.


Version history
===============

- **0.1b**: Original version ``typecheck3000.py`` by
  Dmitry Dvoinikov <dmitry@targeted.org>. See
  http://www.targeted.org/python/recipes/typecheck3000.py

- **0.2b**: Prepared by Lutz Prechelt.
  - Added documentation.
  - Fixed a number of errors in the tests that did not foresee
    that annotations will be checked in a random order.
  - Added ``setup.py``.
  - Replaced the not fully thought-through interpretation of iterables
    by a more specialized handling of tuples and lists.
  - Renamed several of the predicate generators.
  First version that was packaged and uploaded to PyPI.
  **Expect the API to change!**

- **0.3b**:
  - Renamed either_value to enum
  - Renamed either_type to any
  - Renamed matches to has and made it use re.search, not re.match
  - Introduced all and none
  - Introduced a post-installation self-test, because I am not yet
    sure whether it will work on other platforms and with other Python versions
  Feedback is welcome!

Similar packages
================

- ``typecheck3`` is based on the same original code of Dmitry Dvoinikov
  as typecheck-decorator,
  but (as of 0.1.0) lacks the tests, corrections, documentation,
  and API improvements available here.
- ``gradual`` has a similar overall approach of using a decorator and annotations.
  Compared to gradual, typecheck-decorator uses a more pragmatic approach and
  is far more flexible in expressing types.
- ``threecheck`` is similar to typecheck-decorator in
  approach and expressiveness.


TO DO
=====

- use decorator package
- add predicate generator for fixed-structure dict and namedtuple
- add predicate generator for int ranges and float ranges
- replace ``disable()`` by
  ``mode(decorate=True, typecheck=True, collectioncheck_limit=False)``
  collectioncheck_limit is an integer for the maximum number of random
  items to test in a collection (rather than testing all of them)
- add more specialized exception messages, e.g. for sequences and dicts