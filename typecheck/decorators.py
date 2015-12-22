import functools
import inspect

import typecheck.framework as fw

def typecheck(method, *, input_parameter_error=fw.InputParameterError,
              return_value_error=fw.ReturnValueError):
    argspec = inspect.getfullargspec(method)
    if not argspec.annotations or not fw._enabled:
        return method

    default_arg_count = len(argspec.defaults or [])
    non_default_arg_count = len(argspec.args) - default_arg_count

    method_name = method.__name__
    arg_checkers = [None] * len(argspec.args)
    kwarg_checkers = {}
    return_checker = None
    kwarg_defaults = argspec.kwonlydefaults or {}

    for n, v in argspec.annotations.items():
        checker = fw.Checker.create(v)
        if checker is None:
            raise fw.TypeCheckSpecificationError("invalid typecheck for {0}".format(n))
        if n in argspec.kwonlyargs:
            if n in kwarg_defaults and \
                    not checker.check(kwarg_defaults[n]):
                raise fw.TypeCheckSpecificationError(
                    "the default value for {0} is incompatible "
                    "with its typecheck".format(n))
            kwarg_checkers[n] = checker
        elif n == "return":
            return_checker = checker
        else:
            i = argspec.args.index(n)
            if i >= non_default_arg_count and \
                    not checker.check(argspec.defaults[i - non_default_arg_count]):
                raise fw.TypeCheckSpecificationError(
                    "the default value for {0} is incompatible "
                    "with its typecheck".format(n))
            arg_checkers[i] = (n, checker)


    def typecheck_invocation_proxy(*args, **kwargs):
        # Validate positional parameters:
        for check, arg in zip(arg_checkers, args):
            if check is not None:
                arg_name, checker = check
                if not checker.check(arg):
                    raise input_parameter_error(
                        "{0}() has got an incompatible value "
                        "for {1}: {2}".format(method_name, arg_name,
                                              str(arg) == "" and "''" or arg))
        # Validate named parameters:
        for check in arg_checkers:
            if check is not None:
                arg_name, checker = check
                kwarg = kwargs.get(arg_name, fw.Checker.no_value)
                if kwarg != fw.Checker.no_value:
                    if not checker.check(kwarg):
                        raise input_parameter_error(
                            "{0}() has got an incompatible value "
                            "for {1}: {2}".format(method_name, arg_name,
                                                  str(
                                                      kwarg) == "" and "''" or kwarg))
        # Validate kwonly named parameters:
        for arg_name, checker in kwarg_checkers.items():
            kwarg = kwargs.get(arg_name, fw.Checker.no_value)
            if not checker.check(kwarg):
                raise input_parameter_error("{0}() has got an incompatible value "
                                            "for {1}: {2}".format(method_name,
                                                                  arg_name,
                                                                  str(
                                                                      kwarg) == "" and "''" or kwarg))
        # Call method-proper:
        result = method(*args, **kwargs)
        # Check result type:
        if return_checker is not None and not return_checker.check(result):
            raise return_value_error("{0}() has returned an incompatible "
                                     "value: {1}".format(method_name, str(
                result) == "" and "''" or result))
        return result
    #-- end of proxy method

    return functools.update_wrapper(typecheck_invocation_proxy, method,
                                    assigned=("__name__", "__module__", "__doc__"))

################################################################################

_exception_class = lambda t: isinstance(t, type) and issubclass(t, Exception)


#@typecheck
def typecheck_with_exceptions(*,
        input_parameter_error: fw.optional(_exception_class) = fw.InputParameterError,
        return_value_error: fw.optional(_exception_class) = fw.ReturnValueError):
    return lambda method: typecheck(method,
                                    input_parameter_error=input_parameter_error,
                                    return_value_error=return_value_error)

################################################################################
