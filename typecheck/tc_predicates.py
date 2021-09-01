import builtins
import collections.abc
import random
import re as regex_module

import typecheck.framework as fw


def ismapping(annotation):
    return isinstance(annotation, collections.abc.Mapping)


class FixedMappingChecker(fw.Checker):
    def __init__(self, the_mapping):
        self._checks = {key: fw.Checker.create(val)
                        for key, val in the_mapping.items()}

    def check(self, themap, namespace):
        if not ismapping(themap) or len(themap) != len(self._checks):
            return False
        for key, value in themap.items():
            if not key in self._checks or not self._checks[key](value, namespace):
                return False
        return True


fw.Checker.register(ismapping, FixedMappingChecker)


class CallableChecker(fw.Checker):
    """Used if the annotation is a function (which must be predicate)."""
    def __init__(self, callable):
        self._callable = callable

    def check(self, value, namespace):
        return bool(self._callable(value))


fw.Checker.register(builtins.callable, CallableChecker)


################################################################################


class hasattrs(fw.Checker):
    def __init__(self, *attrs):
        self._attrs = attrs
        assert all([type(a) == str for a in attrs])

    def check(self, value, namespace):
        return builtins.all([hasattr(value, attr) for attr in self._attrs])


class re(fw.Checker):
    _regex_eols = {str: "$", bytes: b"$"}
    _value_eols = {str: "\n", bytes: b"\n"}

    def __init__(self, regex):
        self._regex_t = type(regex)
        assert type(regex) in [str, bytes]
        self._regex = regex_module.compile(regex)
        self._regex_eol = regex[-1:] == self._regex_eols.get(self._regex_t)
        self._value_eol = self._value_eols[self._regex_t]

    def check(self, value, namespace):
        return type(value) is self._regex_t and \
               (not self._regex_eol or not value.endswith(self._value_eol)) and \
               self._regex.search(value) is not None


class sequence_of(fw.Checker):
    def __init__(self, check, checkonly=4):
        self._check = fw.Checker.create(check)
        self._checkonly = int(checkonly)
        assert self._checkonly >= 2

    def check(self, value, namespace):
        if len(value) == 0:
            return True
        elif len(value) == 1:
            return self._check.check(value[0], namespace)
        if len(value) <= self._checkonly:
            checkhere = builtins.range(len(value))
        else:
            checkhere = random.sample(builtins.range(1, len(value) - 1),
                                      self._checkonly - 2)  # w/o replacement
            checkhere += [0, len(value) - 1]  # always check first and last
        for idx in checkhere:
            if not self._check.check(value[idx], namespace):
                return False
        return True


class seq_of(sequence_of):
    def check(self, value, namespace):
        return (isinstance(value, collections.abc.Sequence) and
                not isinstance(value, str) and
                super().check(value, namespace))


class list_of(sequence_of):
    def check(self, value, namespace):
        return (isinstance(value, collections.abc.MutableSequence) and
                super().check(value, namespace))


class map_of(fw.Checker):
    def __init__(self, key_check, value_check, checkonly=4):
        self._key_check = fw.Checker.create(key_check)
        self._value_check = fw.Checker.create(value_check)
        self._checkonly = int(checkonly)
        assert self._checkonly >= 1

    def check(self, value, namespace):
        if not isinstance(value, collections.abc.Mapping):
            return False
        count = 0
        for mykey, myvalue in value.items():
            if (not self._key_check.check(mykey, namespace) or
                    not self._value_check.check(myvalue, namespace)):
                return False
            count += 1
            if count == self._checkonly:
                break
        return True


class range(fw.Checker):
    def __init__(self, low, high):
        assert type(low) == type(high)
        self._low = low
        self._high = high
        self._rangetype = type(high)
        assert hasattr(high, "__le__") and hasattr(high, "__ge__")
        # Limitation: presence of le and ge does not guarantee total ordering semantics!
        # And even object() has these attributes. So expect failures.
        assert low < high

    def check(self, value, namespace):
        return (type(value) == self._rangetype and
                value >= self._low and value <= self._high)


class enum(fw.Checker):
    def __init__(self, *values):
        self._values = values

    def check(self, value, namespace):
        return value in self._values


class any(fw.Checker):
    def __init__(self, *args):
        self._checks = tuple(fw.Checker.create(arg) for arg in args)

    def check(self, value, namespace):
        for c in self._checks:
            if c.check(value, namespace):
                return True
        else:
            return False


class all(fw.Checker):
    def __init__(self, *args):
        self._checks = tuple(fw.Checker.create(arg) for arg in args)

    def check(self, value, namespace):
        for c in self._checks:
            if not c.check(value, namespace):
                return False
        else:
            return True


class none(fw.Checker):
    def __init__(self, *args):
        self._checks = tuple(fw.Checker.create(arg) for arg in args)

    def check(self, value, namespace):
        for c in self._checks:
            if c.check(value, namespace):
                return False
        else:
            return True


def anything(x):
    return True
