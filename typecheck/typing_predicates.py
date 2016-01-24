import copy
import inspect
import typing as tg

import typecheck.framework as fw
import typecheck.tc_predicates as tcp

_dummy = None  # __init__.py must use from...import to avoid 'typecheck' name clash

# TypeChecker must not apply to the stuff from module typing
# which all(?) comes under the following types of types.
# We therefore check for these types separately and register their
# checkers with prepend=True so they are handled first.
typing_typetypes = [tg.GenericMeta,
                    tg.CallableMeta,
                    tg._ProtocolMeta]

class GenericMetaChecker(fw.Checker):
    def __init__(self, tg_class):
        self._cls = tg_class

    def check(self, value, namespace):
        if not self._is_possible_subclass(type(value), self._cls):
            return False  # totally the wrong type
        # now check the content of the value, if possible:
        assert type(self._cls) == tg.GenericMeta
        params = self._cls.__parameters__
        result = True  # any failing check will set it to False
        # check checkable relevant properties of all
        # relevant Generic subclasses from the typing module.
        # Fall back from specific to less specific leave the content
        # check out if there are more __parameters__ than expected:
        if (self._we_want_to_check(value, tg.Sequence)):
            return self._check_sequence(value, params, namespace)
        if (self._we_want_to_check(value, tg.Mapping)):
            return self._check_mapping(value, params, namespace)
        if (self._we_want_to_check(value, tg.Iterable)):
            return self._check_by_iterator(value, params, namespace)
        # tg.Iterator: nothing is checkable: reading would modify it
        # tg.Container: nothing is checkable: would need to guess elements
        return True  # no content checking possible

    def _is_possible_subclass(self, subtype, supertype):
        """
        Like issubclass(subtype, supertype) except that TypeVars
        are not taken into account.
        """
        subparams = getattr(subtype, "__parameters__", None)
        if subparams is None:
            return issubclass(subtype, supertype)  # a non-generic actual type
        # It is surprisingly difficult to ignore the type variables in a
        # subclass check. We therefore compare __name__ (along mro) only.
        # This can produce false positives in principle.
        # (previous "nullify __parameters__" logic deleted 2016-01-24 14:52)
        for subtype_super in subtype.mro():
            if subtype_super.__name__ == supertype.__name__:
                # squeeze your thumbs this is not just by accident
                return True  # TODO: ensure __parameters__ are compatible
        return False  # _cls not found as superclass

    def _we_want_to_check(self, value, checkable_class):
        num_parameters = len(checkable_class.__parameters__)
        annotation_is_more_special = self._is_possible_subclass(self._cls, checkable_class)
        annotation_is_less_special = self._is_possible_subclass(checkable_class, self._cls)
        annotation_is_related = (annotation_is_more_special or annotation_is_less_special)
        return (isinstance(value, checkable_class) and
                annotation_is_related and
                len(self._cls.__parameters__) == num_parameters)

    def _check_by_iterator(self, value, contenttypes, namespace):
        assert len(contenttypes) == 1
        checker = fw.Checker.create(contenttypes[0])
        for i, nextvalue in enumerate(value):
            if not checker(nextvalue, namespace):
                return False
            if i+1 == 4:  # TODO: make check-amount configurable
                return True  # enough checks done
        return True  # if shorter than check amount

    def _check_mapping(self, value, contenttypes, namespace):
        assert len(contenttypes) == 2
        return tcp.map_of(contenttypes[0], contenttypes[1]).check(value, namespace)

    def _check_sequence(self, value, contenttypes, namespace):
        assert len(contenttypes) == 1
        return tcp.sequence_of(contenttypes[0]).check(value, namespace)
        # TODO: move sequence content checking routine to fw

fw.Checker.register(fw._is_GenericMeta_class, GenericMetaChecker, prepend=True)


def _is_typevar(annotation):
    return type(annotation) == tg.TypeVar

class TypeVarChecker(fw.Checker):
    def __init__(self, typevar):
        self.typevar = typevar

    def check(self, value, namespace):
        """
        See whether the TypeVar is bound for the first time
        or is met with _exactly_ the same type as previously.
        That type must also obey the TypeVar's bound, if any.
        Everything else is a type error.
        """
        return namespace.is_compatible(self.typevar, type(value))
        # TODO: more informative error message, showing the TypeVar binding

fw.Checker.register(_is_typevar, TypeVarChecker, prepend=True)


def _is_tg_tuple(annotation):
    return (inspect.isclass(annotation) and
            issubclass(annotation, tg.Tuple) and
            not type(annotation) == tuple)

class TupleChecker(fw.FixedSequenceChecker):
    def __init__(self, tg_tuple_class):
        self._cls = tg_tuple_class
        self._checks = tuple(fw.Checker.create(t) for t in self._cls.__tuple_params__)

    # check() is inherited

fw.Checker.register(_is_tg_tuple, TupleChecker, prepend=True)


def _is_tg_namedtuple(annotation):
    return (inspect.isclass(annotation) and
            issubclass(annotation, tuple) and
            getattr(annotation, "_field_types"))

class NamedTupleChecker(fw.Checker):
    def __init__(self, tg_namedtuple_class):
        self._cls = tg_namedtuple_class
        self._checks = tuple(fw.Checker.create(self._cls._field_types[fn])
                             for fn in self._cls._fields)

    def check(self, value, namespace):
        """
        Attribute _field_types is a dict from field name to type.
        """
        if (not issubclass(type(value), self._cls) or
            len(value) != len(self._cls._fields)):
            return False
        for i, check in enumerate(self._checks):
            if not check(value[i], namespace):
                return False
        return True

# must be registered after TupleChecker (to be executed before it):
fw.Checker.register(_is_tg_namedtuple, NamedTupleChecker, prepend=True)


def _is_tg_union(annotation):
    return issubclass(annotation, tg.Union)

class UnionChecker(fw.Checker):
    def __init__(self, tg_union_class):
        self._cls = tg_union_class
        self._checks = tuple(fw.Checker.create(p) for p in self._cls.__union_params__)

    def check(self, value, namespace):
        """
        Attribute _field_types is a dict from field name to type.
        """
        for i, check in enumerate(self._checks):
            if check(value, namespace):
                return True
        return False

# must be registered after TupleChecker (to be executed before it):
fw.Checker.register(_is_tg_union, UnionChecker, prepend=True)


def _is_string(annotation):
    return type(annotation) == str

class TypeNameChecker(fw.Checker):
    def __init__(self, typename):
        self._typename = typename

    def check(self, value, namespace):
        return type(value).__name__ == self._typename
        # TODO: handle complex forward references such as 'mymodule.MyClass'

# Should be the second type registered, because strings are sequences so that
# FixedTupleChecker is keen to intervene.
fw.Checker.register(_is_string, TypeNameChecker, prepend=True)


########## and finally:

def _is_tg_any(annotation):
    return annotation == tg.Any

class AnyChecker(fw.Checker):
    def __init__(self, tg_any_class):
        self._cls = tg_any_class

    def check(self, value, namespace):
        return True

# Must be the very first type registered, because issubclass(Any, Xtype)
# is always true, so every other predicate would also react to an Any
# annotation but its checker will often make assumptions that are incorrect.
fw.Checker.register(_is_tg_any, AnyChecker, prepend=True)
