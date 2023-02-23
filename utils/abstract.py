from abc import ABCMeta, ABC, abstractmethod


# pylint: disable=too-few-public-methods


__all__ = [
    "isabstract",
    "abstractmethod",
    "abstractclsattrib",
    "ABCMeta",
    "ABC"
]


CHECKER_ATTRIBUTE_NAME = '___abstractchecker___'


def _ischecker(value):
    return hasattr(value, CHECKER_ATTRIBUTE_NAME)


def isabstract(cls):
    # There is no standard way to get abstract methods, so it may work only in CPython
    if not hasattr(cls, '__abstractmethods__'):
        return False
    return len(cls.__abstractmethods__) != 0


def abstractclsattrib(checker):
    result = abstractmethod(checker)
    setattr(result, CHECKER_ATTRIBUTE_NAME, checker)
    return result


class _AbstractCheckerMeta(ABCMeta):

    def __init__(cls, name, bases, namespace, **kwargs):
        super().__init__(name, bases, namespace, **kwargs)
        if isabstract(cls):
            return
        checkers = {k: v for base in reversed(cls.__mro__) for k, v in base.__dict__.items() if _ischecker(v)}
        for attrib, checker in checkers.items():
            checker(cls, getattr(cls, attrib))


class _AbstractChecker(ABC, metaclass=_AbstractCheckerMeta):
    pass


ABCMeta = _AbstractCheckerMeta
ABC = _AbstractChecker
