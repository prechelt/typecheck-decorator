
import inspect

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

class optional(Checker):
    def __init__(self, check):
        self._check = Checker.create(check)

    def check(self, value):
        return value is Checker.no_value or value is None or self._check.check(value)