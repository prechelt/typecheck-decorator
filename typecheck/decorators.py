import functools
import inspect
import typing as tg

import typecheck.framework as fw

def typecheck(method, *, input_parameter_error=fw.InputParameterError,
              return_value_error=fw.ReturnValueError):
    argspec = inspect.getfullargspec(method)
    argnames = argspec.args
    if not argspec.annotations or not fw._enabled:
        return method

    default_arg_count = len(argspec.defaults or [])
    non_default_arg_count = len(argnames) - default_arg_count

    method_name = method.__name__
    arg_checkers = [None] * len(argnames)
    kwarg_checkers = {}
    return_checker = None
    kwarg_defaults = argspec.kwonlydefaults or {}

    for n, v in argspec.annotations.items():
        # namespace for defaults w TypeVars; bindings will be forgotten!:
        namespace = fw.TypeVarNamespace()
        checker = fw.Checker.create(v)
        if checker is None:
            raise fw.TypeCheckSpecificationError("invalid typecheck for {0}".format(n))
        if n in argspec.kwonlyargs:
            if n in kwarg_defaults and \
                    not checker.check(kwarg_defaults[n], namespace):
                raise fw.TypeCheckSpecificationError(
                    "the default value for {0} is incompatible "
                    "with its typecheck".format(n))
            kwarg_checkers[n] = checker
        elif n == "return":
            return_checker = checker
        else:
            i = argspec.args.index(n)
            if i >= non_default_arg_count and \
                    not checker.check(argspec.defaults[i - non_default_arg_count],
                                      namespace):
                raise fw.TypeCheckSpecificationError(
                    "the default value for {0} is incompatible "
                    "with its typecheck".format(n))
            arg_checkers[i] = (n, checker)


    def typecheck_invocation_proxy(*args, **kwargs):
        # TODO: '.' not in method_name  for methods. Why not?
        if len(argnames) > 0 and argnames[0] == 'self':
            theself = args[0]  # call to instance method
        else:
            theself = None  # call to function, static method, or class method
        namespace = fw.TypeVarNamespace(theself)
        # Validate positional parameters:
        for declaration, arg in zip(arg_checkers, args):
            if declaration is not None:
                arg_name, checker = declaration
                if not checker.check(arg, namespace):
                    raise input_parameter_error(
                        "{0}() has got an incompatible value "
                        "for {1}: {2}".format(method_name, arg_name,
                                              str(arg) == "" and "''" or arg))
        # Validate named parameters:
        for declaration in arg_checkers:
            if declaration is not None:
                arg_name, checker = declaration
                kwarg = kwargs.get(arg_name, fw.Checker.no_value)
                if kwarg != fw.Checker.no_value:
                    if not checker.check(kwarg, namespace):
                        raise input_parameter_error(
                            "{0}() has got an incompatible value "
                            "for {1}: {2}".format(method_name, arg_name,
                                                  str(
                                                      kwarg) == "" and "''" or kwarg))
        # Validate kwonly named parameters:
        for arg_name, checker in kwarg_checkers.items():
            kwarg = kwargs.get(arg_name, fw.Checker.no_value)
            if not checker.check(kwarg, namespace):
                raise input_parameter_error("{0}() has got an incompatible value "
                                            "for {1}: {2}".format(method_name,
                                                                  arg_name,
                                                                  str(
                                                                      kwarg) == "" and "''" or kwarg))
        # Call method-proper:
        result = method(*args, **kwargs)
        # Check result type:
        if (return_checker is not None and
                not return_checker.check(result, namespace)):
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

# TODO: @dynamictypecheck as @typecheck plus @typing.no_type_check:
# dynamictypecheck = tg.no_type_check_decorator(typecheck)
