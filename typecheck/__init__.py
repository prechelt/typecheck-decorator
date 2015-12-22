# Parameter/return value type checking for Python3 using function annotations.
#
# (c) 2008-2012 Dmitry Dvoinikov <dmitry@targeted.org>
# (c) 2014-2016 Lutz Prechelt
# Distributed under BSD license.

__version__ = "1.2"

__all__ = [
    # decorators:
    "typecheck", "typecheck_with_exceptions",
    # check predicate generators:
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
    "enable",  # deprecated
]

from .decorators import typecheck, typecheck_with_exceptions
from .framework import (TypeCheckError, InputParameterError, ReturnValueError,
                        TypeCheckSpecificationError,
                        optional, disable, enable)
from .tc_predicates import *
