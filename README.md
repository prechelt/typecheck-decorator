typecheck-decorator
###################

A decorator for functions, `@typecheck`, to be used together with
Python3 annotations on function parameters and function results.
The decorator will perform dynamic argument type checking for every call to the function.

Introduction: A quick example
==============================

  ```Python
  @typecheck
  def foo1(a:int, b=None, c:str="mydefault") -> bool :
      print(a, b, c)
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
will be evaluated with the ``type()`` function and the result compared
to the annotated type.

If any argument has the wrong type, a ``TypeCheckError`` exception will be raised.
Class types and collection types can be annotated as well, but that
is *by far* not the end of the story.


Importing
=========

The recommended usage style is with the following imports:

  ```Python
  from typecheck import typecheck    # for the decorator
  import typecheck as tc             # for clarity for all other objects
  ```


Concepts
========

``@typecheck`` allows three different types of annotation:
- **Types.** More precisely: expressions returning a type, that is,
  for which ``inspect.isclass`` evaluates to True.
  This could also be a function call or type variable.
  If the annotation declares type ``T``, the argument ``x`` must fulfil
  ``isinstance(x, T)``, so objects from subclasses of T are acceptable as well.
- **Iterables.** The annotation provides an iterable object that

- **Predicates.** The annotation provides a function (or in fact any callable) that accepts
  the respective argument and returns a value that evaluates to
  True (for an acceptable argument)
  or False (for all others).
  Note that a predicate is a function, not a function call.

