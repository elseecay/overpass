import secrets
import platform
import functools


# pylint: disable=too-few-public-methods


def is_os_windows() -> bool:
    return "WINDOWS" in platform.platform().upper()


def is_os_linux() -> bool:
    return "LINUX" in platform.platform().upper()


def random_bytes(size: int) -> bytes:
    return secrets.token_bytes(size)


def split_bytes(data: bytes, *sizes, full_coverage=True):
    result = []
    begin, end = 0, 0
    for s in sizes:
        end += s
        result.append(data[begin:end])
        begin = end
    if end > len(data):
        raise IndexError("Out of bounds")
    if end < len(data) and full_coverage:
        raise IndexError("Not covered")
    return result


def serial_call(arg, *functions):
    return functools.reduce(lambda cur, f: f(cur), functions, arg)


def typename(obj) -> str:
    if isinstance(obj, type):
        return obj.__name__
    return obj.__class__.__name__


class SetAttribute:

    def __init__(self, **attribs):
        self.attribs = attribs

    def __call__(self, obj):
        for name, value in self.attribs.items():
            setattr(obj, name, value)
        return obj


class FreeOnError:

    def __init__(self, resource, free_action):
        self.resource = resource
        self.free_action = free_action

    def __enter__(self):
        return self.resource

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.free_action()


class CloseOnError(FreeOnError):

    def __init__(self, resource):
        super().__init__(resource, resource.close)
