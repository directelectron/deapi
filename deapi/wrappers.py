import warnings
from functools import wraps
import logging

from numpy.exceptions import VisibleDeprecationWarning

log = logging.getLogger("DECameraClientLib")


def write_only(func):
    def wrapper(*args, **kwargs):
        if args[0].read_only:
            log.error("Client is read-only. Cannot set property.")
            return
        else:
            return func(*args, **kwargs)

    return wrapper


def disable_scan(func):
    def wrapper(*args, **kwargs):
        print("Disabling scan")
        initial_scan = args[0]["Scan - Enable"]
        args[0].set_property("Scan - Enable", False)
        ans = func(*args, **kwargs)
        args[0].set_property("Scan - Enable", initial_scan)
        return ans

    return wrapper


class deprecated_argument:
    """Decorator to remove an argument from a function or method's
    signature.

    Adapted from `scikit-image
    <https://github.com/scikit-image/scikit-image/blob/main/skimage/_shared/utils.py>`_.
    """

    def __init__(self, name, since, removal=None, alternative=None):
        self.name = name
        self.since = since
        self.removal = removal
        self.alternative = alternative

    def __call__(self, func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            if self.name in kwargs.keys():
                msg = (
                    f"Argument `{self.name}` is deprecated. To avoid this warning, please do not use "
                    f"`{self.name}`. "
                )
                if self.alternative is not None:
                    msg += f"Use `{self.alternative}` instead. "
                    kwargs[self.alternative] = kwargs.pop(
                        self.name
                    )  # replace with alternative kwarg
                msg += f"See the documentation of `{func.__name__}()` for more details."
                warnings.simplefilter(
                    action="always", category=VisibleDeprecationWarning
                )
                func_code = func.__code__
                warnings.warn_explicit(
                    message=msg,
                    category=VisibleDeprecationWarning,
                    filename=func_code.co_filename,
                    lineno=func_code.co_firstlineno + 1,
                )
            return func(*args, **kwargs)

        return wrapped
