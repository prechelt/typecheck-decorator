import re

class expected:
    def __init__(self, e, msg_regexp=None):
        if isinstance(e, Exception):
            self._type, self._msg = e.__class__, str(e)
        elif isinstance(e, type) and issubclass(e, Exception):
            self._type, self._msg = e, msg_regexp
        else:
            raise Exception("usage: 'with expected(Exception)'")

    def __enter__(self):  # make this a context handler
        try:
            pass
        except:
            pass  # this is a Python3 way of saying sys.exc_clear()

    def __exit__(self, exc_type, exc_value, traceback):
        assert exc_type is not None, \
            "expected {0:s} to have been thrown".format(self._type.__name__)
        msg = str(exc_value)
        return (issubclass(exc_type, self._type) and
                (self._msg is None or
                 msg.startswith(self._msg) or  # for instance
                 re.match(self._msg, msg)))  # for class + regexp
