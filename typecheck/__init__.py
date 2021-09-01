# Parameter/return value type checking for Python3 using function annotations.
#
# (c) 2008-2012 Dmitry Dvoinikov <dmitry@targeted.org>
# (c) 2014-2016 Lutz Prechelt
# Distributed under BSD license.

__version__ = "1.3"

from .framework import (TypeCheckError, InputParameterError, ReturnValueError,
                        TypeCheckSpecificationError,
                        optional, disable, enable)
from .decorators import typecheck, typecheck_with_exceptions
from .typing_predicates import _dummy  # registers checkers
from .tc_predicates import (hasattrs, re,
                            seq_of, list_of, map_of,
                            range, enum,
                            any, all, none, anything,
                           )
