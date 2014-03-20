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

# check predicates:
"optional", "hasattrs", "matches",
"sequence_of", "tuple_of", "list_of", "dict_of",
"either_value", "either_type", "anything",

# exceptions:
"TypeCheckError", "InputParameterError", "ReturnValueError",
"TypeCheckSpecificationError",

# utility methods:
"disable",  # deprecated

]

################################################################################

import inspect
import functools
import re

callable = lambda x: hasattr(x, "__call__")
anything = lambda x: True

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

################################################################################

issequence = lambda x: isinstance(x, tuple) or isinstance(x, list)

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

################################################################################

class CallableChecker(Checker):

    def __init__(self, callable):
        self._callable = callable

    def check(self, value):
        return bool(self._callable(value))

Checker.register(callable, CallableChecker)

################################################################################

class OptionalChecker(Checker):

    def __init__(self, check):
        self._check = Checker.create(check)

    def check(self, value):
        return value is Checker.no_value or value is None or self._check.check(value)

optional = OptionalChecker

################################################################################

class HasAttrChecker(Checker):

    def __init__(self, *attrs):
        self._attrs = attrs

    def check(self, value):
        return all([hasattr(value, attr) for attr in self._attrs])

hasattrs = HasAttrChecker

################################################################################

class RegexChecker(Checker):

    _regex_eols = { str: "$", bytes: b"$" }
    _value_eols = { str: "\n", bytes: b"\n" }

    def __init__(self, regex):
        self._regex_t = type(regex)
        self._regex = re.compile(regex)
        self._regex_eol = regex[-1:] == self._regex_eols.get(self._regex_t)
        self._value_eol = self._value_eols[self._regex_t]

    def check(self, value):
        return type(value) is self._regex_t and \
               (not self._regex_eol or not value.endswith(self._value_eol)) and \
               self._regex.match(value) is not None

matches = RegexChecker

################################################################################

class SequenceOfChecker(Checker):

    def __init__(self, check):
        self._check = Checker.create(check)
        self._allowable_types = (list, tuple)

    def check(self, value):
        return any([isinstance(value, t) for t in self._allowable_types]) and \
               functools.reduce(lambda r, v: r and self._check.check(v), value, True)

sequence_of = SequenceOfChecker

################################################################################

class TupleOfChecker(SequenceOfChecker):

    def __init__(self, check):
        self._check = Checker.create(check)
        self._allowable_types = (tuple,)

tuple_of = TupleOfChecker

################################################################################

class ListOfChecker(SequenceOfChecker):

    def __init__(self, check):
        self._check = Checker.create(check)
        self._allowable_types = (list,)

list_of = ListOfChecker

################################################################################

class DictOfChecker(Checker):

    def __init__(self, key_check, value_check):
        self._key_check = Checker.create(key_check)
        self._value_check = Checker.create(value_check)

    def check(self, value):
        return isinstance(value, dict) and \
               functools.reduce(lambda r, t: r and self._key_check.check(t[0]) and \
                                             self._value_check.check(t[1]),
                                value.items(), True)

dict_of = DictOfChecker

################################################################################

class EitherValueChecker(Checker):

    def __init__(self, *values):
        self._values = values

    def check(self, value):
        return value in self._values

either_value = EitherValueChecker

################################################################################

class EitherTypeChecker(Checker):

    def __init__(self, *args):
        self._checks = tuple(Checker.create(arg) for arg in args)

    def check(self, value):
        for c in self._checks:
            if c.check(value):
                return True
        else:
            return False

either_type = EitherTypeChecker

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
