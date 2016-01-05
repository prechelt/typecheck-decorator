
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

    def __call__(self, value):
        return self.check(value)


################################################################################

class TypeChecker(Checker):
    def __init__(self, cls):
        self._cls = cls

    def check(self, value):
        return isinstance(value, self._cls)

# Note: 'typing'-module checkers must register _before_ this one:
Checker.register(inspect.isclass, TypeChecker)

################################################################################

class optional(Checker):
    def __init__(self, check):
        self._check = Checker.create(check)

    def check(self, value):
        return value is Checker.no_value or value is None or self._check.check(value)