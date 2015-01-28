#-*- coding: iso-8859-1 -*-
################################################################################
#
# Parameter/return value type checking for Python3 using function annotations.
#
# (c) 2008-2012 Dmitry Dvoinikov <dmitry@targeted.org>
# (c) 2014 Lutz Prechelt
# Distributed under BSD license.

__all__ = [
# decorators:
  "typecheck", "typecheck_with_exceptions",
# check predicate generators:
  "optional",
  "hasattrs", "re",
  "seq_of", "list_of", "map_of",
  "range", "enum",
  "any", "all", "none",
# check predicate generators:
  "anything",
# exceptions:
  "TypeCheckError", "InputParameterError", "ReturnValueError",
  "TypeCheckSpecificationError",
# utility methods:
  "disable",  # deprecated
]

import builtins
import collections
import inspect
import functools
import random
import re as regex_module

################################################################################

_enabled = True

def disable():
    global _enabled
    _enabled = False

################################################################################

class TypeCheckError(Exception): pass
class TypeCheckSpecificationError(Exception): pass
class InputParameterError(TypeCheckError): pass
class ReturnValueError(TypeCheckError): pass

################################################################################

class Checker:

    class NoValue:
        def __str__(self):
            return "<no value>"
    no_value = NoValue()

    _registered = []

    @classmethod
    def register(cls, predicate, factory):
        cls._registered.append((predicate, factory))

    @classmethod
    def create(cls, value):
        if isinstance(value, cls):
            return value
        for predicate, factory in cls._registered:
            if predicate(value):
                return factory(value)
        else:
            return None

    def __call__(self, value):
        return self.check(value)

################################################################################

class TypeChecker(Checker):

    def __init__(self, cls):
        self._cls = cls

    def check(self, value):
        return isinstance(value, self._cls)

Checker.register(inspect.isclass, TypeChecker)


def issequence(x):
    return isinstance(x, collections.Sequence)

class FixedSequenceChecker(Checker):

    def __init__(self, the_sequence):
        self._cls = type(the_sequence)
        self._checks = tuple(Checker.create(x) for x in iter(the_sequence))

    def check(self, values):
        """specifying a plain tuple allows arguments that are tuples or lists;
        specifying a specialized (subclassed) tuple allows only that type;
        specifying a list allows only that list type."""
        if not issequence(values):
            return False
        if self._cls == tuple or isinstance(values, self._cls):
            if len(values) != len(self._checks):  return False
            for thischeck, thisvalue in zip(self._checks, values):
                if not thischeck(thisvalue): return False
            return True
        else:
            return False

Checker.register(issequence, FixedSequenceChecker)


def isnamedtuple(x):
    return isinstance(x, tuple) and ismapping(x.__dict__)

def ismapping(x):
    return isinstance(x, collections.Mapping)

class FixedMappingChecker(Checker):

    def __init__(self, the_mapping):
        self._checks = { key: Checker.create(val)
                         for key,val in the_mapping.items() }

    def check(self, themap):
        if isnamedtuple(themap):
            themap = vars(themap)
            assert ismapping(themap)
        if not ismapping(themap) or len(themap) != len(self._checks):
            return False
        for key, value in themap.items():
                if not key in self._checks or not self._checks[key](value):
                    return False
        return True

Checker.register(ismapping, FixedMappingChecker)


class CallableChecker(Checker):

    def __init__(self, callable):
        self._callable = callable

    def check(self, value):
        return bool(self._callable(value))

Checker.register(builtins.callable, CallableChecker)

################################################################################

class optional(Checker):
    def __init__(self, check):
        self._check = Checker.create(check)

    def check(self, value):
        return value is Checker.no_value or value is None or self._check.check(value)


class hasattrs(Checker):
    def __init__(self, *attrs):
        self._attrs = attrs
        assert all([type(a) == str for a in attrs])

    def check(self, value):
        return builtins.all([hasattr(value, attr) for attr in self._attrs])


class re(Checker):
    _regex_eols = { str: "$", bytes: b"$" }
    _value_eols = { str: "\n", bytes: b"\n" }

    def __init__(self, regex):
        self._regex_t = type(regex)
        assert type(regex) in [str, bytes]
        self._regex = regex_module.compile(regex)
        self._regex_eol = regex[-1:] == self._regex_eols.get(self._regex_t)
        self._value_eol = self._value_eols[self._regex_t]

    def check(self, value):
        return type(value) is self._regex_t and \
               (not self._regex_eol or not value.endswith(self._value_eol)) and \
               self._regex.search(value) is not None


class sequence_of(Checker):

    def __init__(self, check, checkonly=4):
        self._check = Checker.create(check)
        self._checkonly = int(checkonly)
        assert self._checkonly >= 2

    def check(self, value):
        if len(value) == 0:
            return True
        elif len(value) == 1:
            return self._check.check(value[0])
        if len(value) <= self._checkonly:
            checkhere = builtins.range(len(value))
        else:
            checkhere = random.sample(builtins.range(1,len(value)-1),
                                      self._checkonly-2)
            checkhere += [0, len(value)-1]  # always check first and last
        for idx in checkhere:
            if not self._check.check(value[idx]):
                return False
        return True


class seq_of(sequence_of):
    def check(self, value):
        return (isinstance(value, collections.Sequence) and
                not isinstance(value, str) and 
                super().check(value))


class list_of(sequence_of):
    def check(self, value):
        return (isinstance(value, collections.MutableSequence) and
                super().check(value))


class map_of(Checker):

    def __init__(self, key_check, value_check, checkonly=4):
        self._key_check = Checker.create(key_check)
        self._value_check = Checker.create(value_check)
        self._checkonly = int(checkonly)
        assert self._checkonly >= 1

    def check(self, value):
        if not isinstance(value, collections.Mapping):
            return False
        count = 0
        for mykey, myvalue in value.items():
            if not self._key_check.check(mykey) or \
               not self._value_check.check(myvalue):
                return False
            count += 1
            if count == self._checkonly:
                break
        return True

class range(Checker):

    def __init__(self, low, high):
        assert type(low) == type(high)
        self._low = low
        self._high = high
        self._rangetype = type(high)
        assert hasattr(high, "__le__") and hasattr(high, "__ge__")
        # Limitation: presence of le and ge does not guarantee total ordering semantics!
        # And even object() has these attributes. So expect failures.
        assert low < high

    def check(self, value):
        return (type(value) == self._rangetype and
                value >= self._low and value <= self._high)


class enum(Checker):

    def __init__(self, *values):
        self._values = values

    def check(self, value):
        return value in self._values


class any(Checker):

    def __init__(self, *args):
        self._checks = tuple(Checker.create(arg) for arg in args)

    def check(self, value):
        for c in self._checks:
            if c.check(value):
                return True
        else:
            return False


class all(Checker):

    def __init__(self, *args):
        self._checks = tuple(Checker.create(arg) for arg in args)

    def check(self, value):
        for c in self._checks:
            if not c.check(value):
                return False
        else:
            return True


class none(Checker):

    def __init__(self, *args):
        self._checks = tuple(Checker.create(arg) for arg in args)

    def check(self, value):
        for c in self._checks:
            if c.check(value):
                return False
        else:
            return True


def anything(x):
    return True

################################################################################

def typecheck(method, *, input_parameter_error = InputParameterError,
                         return_value_error = ReturnValueError):

    argspec = inspect.getfullargspec(method)
    if not argspec.annotations or not _enabled:
        return method

    default_arg_count = len(argspec.defaults or [])
    non_default_arg_count = len(argspec.args) - default_arg_count

    method_name = method.__name__
    arg_checkers = [None] * len(argspec.args)
    kwarg_checkers = {}
    return_checker = None
    kwarg_defaults = argspec.kwonlydefaults or {}

    for n, v in argspec.annotations.items():
        checker = Checker.create(v)
        if checker is None:
            raise TypeCheckSpecificationError("invalid typecheck for {0}".format(n))
        if n in argspec.kwonlyargs:
            if n in kwarg_defaults and \
               not checker.check(kwarg_defaults[n]):
                raise TypeCheckSpecificationError("the default value for {0} is incompatible "
                                                  "with its typecheck".format(n))
            kwarg_checkers[n] = checker
        elif n == "return":
            return_checker = checker
        else:
            i = argspec.args.index(n)
            if i >= non_default_arg_count and \
               not checker.check(argspec.defaults[i - non_default_arg_count]):
                raise TypeCheckSpecificationError("the default value for {0} is incompatible "
                                                  "with its typecheck".format(n))
            arg_checkers[i] = (n, checker)

    def typecheck_invocation_proxy(*args, **kwargs):

        for check, arg in zip(arg_checkers, args):
            if check is not None:
                arg_name, checker = check
                if not checker.check(arg):
                    raise input_parameter_error("{0}() has got an incompatible value "
                                                "for {1}: {2}".format(method_name, arg_name,
                                                                      str(arg) == "" and "''" or arg))

        for arg_name, checker in kwarg_checkers.items():
            kwarg = kwargs.get(arg_name, Checker.no_value)
            if not checker.check(kwarg):
                raise input_parameter_error("{0}() has got an incompatible value "
                                            "for {1}: {2}".format(method_name, arg_name,
                                                                  str(kwarg) == "" and "''" or kwarg))

        result = method(*args, **kwargs)

        if return_checker is not None and not return_checker.check(result):
            raise return_value_error("{0}() has returned an incompatible "
                                     "value: {1}".format(method_name, str(result) == "" and "''" or result))

        return result

    return functools.update_wrapper(typecheck_invocation_proxy, method,
                                    assigned = ("__name__", "__module__", "__doc__"))

################################################################################

_exception_class = lambda t: isinstance(t, type) and issubclass(t, Exception)

@typecheck
def typecheck_with_exceptions(*, input_parameter_error: optional(_exception_class) = InputParameterError,
                                 return_value_error: optional(_exception_class) = ReturnValueError):

    return lambda method: typecheck(method, input_parameter_error = input_parameter_error,
                                            return_value_error = return_value_error)

################################################################################

