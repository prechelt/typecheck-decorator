import collections
import inspect
import typing as tg

################################################################################

_enabled = True


def disable():
    global _enabled
    _enabled = False

def enable():
    global _enabled
    _enabled = True

################################################################################

class TypeCheckError(Exception): pass


class TypeCheckSpecificationError(Exception): pass


class InputParameterError(TypeCheckError): pass


class ReturnValueError(TypeCheckError): pass

################################################################################

def _is_GenericMeta_class(annotation):
    return (inspect.isclass(annotation) and
            type(annotation) == tg.GenericMeta)

class TypeVarNamespace:
    """
    TypeVarNamespace objects hold TypeVar bindings.

    Consists of two sub-namespaces:
    A dictionary holding pairs of a TypeVar object and a type object
    for the call-level scope of a single function call
    and a similar dictionary for the instance-level scope of bindings for the
    type parameters of generic classes.
    The latter is stored as attribute NS_ATTRIBUTE in the class instance itself.
    Most TypeVarNamespace objects will never be used after their creation.
    is_compatible() implements bound, covariance, and contravariance logic.
    """
    NS_ATTRIBUTE = '__tc_bindings__'

    def __init__(self, instance=None):
        """_instance is the self of the method call if the class is a tg.Generic"""
        self._ns = dict()
        self._instance = instance
        self._instance_ns = (self._instance and
                             self._instance.__dict__.get(self.NS_ATTRIBUTE))

    def bind(self, typevar, its_type):
        """
        Binds typevar to the type its_type.
        Binding occurs on the instance if the typevar is a TypeVar of the
        generic type of the instance, on call level otherwise.
        """
        assert type(typevar) == tg.TypeVar
        if self.is_generic_in(typevar):
            self.bind_to_instance(typevar, its_type)
        else:
            self._ns[typevar] = its_type

    def is_generic_in(self, typevar):
        if not _is_GenericMeta_class(type(self._instance)):
            return False
        # TODO: Is the following really sufficient?:
        return typevar in self._instance.__parameters__

    def bind_to_instance(self, typevar, its_type):
        if self._instance_ns is None:  # we've not bound something previously:
            self._instance.__setattr__(self.NS_ATTRIBUTE, dict())
            self._instance_ns = self._instance.__dict__[self.NS_ATTRIBUTE]
        self._instance_ns[typevar] = its_type

    def is_bound(self, typevar):
        if typevar in self._ns:
            return True
        return self._instance_ns and typevar in self._instance_ns

    def binding_of(self, typevar):
        """Returns the type the typevar is bound to, or None."""
        if typevar in self._ns:
            return self._ns[typevar]
        if self._instance_ns and typevar in self._instance_ns:
            return self._instance_ns[typevar]
        return None

    def is_compatible(self, typevar, its_type):
        """
        Checks whether its_type conforms to typevar.
        If the typevar is not yet bound, it will be bound to its_type.
        The covariance/contravariance checking described in the respective section
        of PEP484 applies to declared types, but here we have actual types;
        therefore, (1) subtypes are always compatible, (2) we may have to
        rebind the type variable to supertypes of the current binding several
        times until the required most general binding is found.
        """
        result = True
        binding = self.binding_of(typevar)  # may or may not exist
        if binding is None:
            self.bind(typevar, its_type)  # initial binding, OK
        elif issubclass(binding, its_type):
            self.bind(typevar, its_type)  # rebind to supertype, OK
        elif not issubclass(its_type, binding):  # accept like TypeChecker
            return False
        binding = self.binding_of(typevar)  # will now exist
        if (typevar.__bound__ and
                not issubclass(binding, typevar.__bound__)):
            return False  # bound violation
        if (len(typevar.__constraints__) > 0 and
                not issubclass(binding, tg.Union[typevar.__constraints__])):
            return False  # constraint violation
        return True

################################################################################

class Checker:
    class NoValue:
        def __str__(self):
            return "<no value>"

    no_value = NoValue()

    _registered = []

    @classmethod
    def register(cls, predicate, factory, prepend=False):
        """
        Adds another type X of typecheck annotations to the framework.
        predicate(annot) indicates whether annot has annotation type X;
        factory(annot) creates the appropriate typechecker instance.
        The checker type is normally added after the existing ones,
        but 'prepend' makes it come first.
        """
        if prepend:
            cls._registered.insert(0, (predicate, factory))
        else:
            cls._registered.append((predicate, factory))

    @classmethod
    def create(cls, annotation_or_checker):
        if isinstance(annotation_or_checker, cls):
            return annotation_or_checker  # is a checker already
        annotation = annotation_or_checker
        for predicate, factory in cls._registered:
            if predicate(annotation):
                return factory(annotation)
        else:
            return None

    def __call__(self, value, namespace):
        return self.check(value, namespace)


################################################################################

class TypeChecker(Checker):
    def __init__(self, cls):
        self._cls = cls

    def check(self, value, namespace):
        # return isinstance(value, self._cls)  # does not work for tg.Protocol
        return issubclass(type(value), self._cls)

# Note: 'typing'-module checkers must register _before_ this one:
Checker.register(inspect.isclass, TypeChecker)

################################################################################

class optional(Checker):
    def __init__(self, check):
        self._check = Checker.create(check)

    def check(self, value, namespace):
        return (value is Checker.no_value or
                value is None or
                self._check.check(value, namespace))

################################################################################

def _is_sequence(annotation):
    return isinstance(annotation, collections.Sequence)


class FixedSequenceChecker(Checker):
    def __init__(self, the_sequence):
        self._cls = type(the_sequence)
        self._checks = tuple(Checker.create(x) for x in iter(the_sequence))

    def check(self, values, namespace):
        """specifying a plain tuple allows arguments that are tuples or lists;
        specifying a specialized (subclassed) tuple allows only that type;
        specifying a list allows only that list type."""
        is_tuplish_type = (issubclass(self._cls, tg.Tuple) or
                           issubclass(type(values), self._cls))
        if (not _is_sequence(values) or not is_tuplish_type or
                len(values) != len(self._checks)):
            return False
        for thischeck, thisvalue in zip(self._checks, values):
            if not thischeck(thisvalue, namespace):
                return False
        return True


Checker.register(_is_sequence, FixedSequenceChecker)

################################################################################

