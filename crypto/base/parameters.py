from functools import wraps

from utils.abstract import *


__all__ = [
    "ParametersContainerMeta",
    "ParametersContainer",
    "Parameter",
    "parameters_init_simplifier"
]


CLASS_PARAMETERS_ATTRIBUTE_NAME = "___parameters___"
PARAMETER_ATTRIBUTE_PREFIX = "___parameter___"


class Parameter:

    # pylint: disable-next=invalid-name,too-few-public-methods
    class NO_VAL: pass

    def __init__(self, vtype: type, *, required=True, default=NO_VAL):
        self.vtype = vtype
        self.required = required
        self.default = default

    def __call__(self, checker):
        # pylint: disable=attribute-defined-outside-init
        self.name = checker.__name__
        self.checker = checker
        self.attribute_name = PARAMETER_ATTRIBUTE_PREFIX + self.name
        return self

    def __get__(self, instance, owner=None):
        if not instance:
            return self
        return self._getval(instance)

    def __set__(self, instance, value):
        self.check(instance, value)
        self._setval(instance, value)

    def is_set(self, instance) -> bool:
        return self.attribute_name in vars(instance)

    def check(self, instance, value):
        assert isinstance(value, self.vtype), f"Invalid value type for parameter {self.name}"
        self.checker(instance, value)

    def set_unchecked(self, instance, value):
        self._setval(instance, value)

    def _getval(self, instance):
        return getattr(instance, self.attribute_name)

    def _setval(self, instance, value):
        return setattr(instance, self.attribute_name, value)


class ParametersContainerMeta(type):

    def __init__(cls, name, bases, namespace):
        # pylint: disable=no-value-for-parameter
        super().__init__(name, bases, namespace)
        cls._set_parameters()

    def _set_parameters(cls):
        localprms = frozenset(k for k, v in cls.__dict__.items() if isinstance(v, Parameter))
        basesprms = frozenset(k for base in cls.__mro__ for k in getattr(base, CLASS_PARAMETERS_ATTRIBUTE_NAME, tuple()) if isinstance(getattr(base, k, None), Parameter))
        setattr(cls, CLASS_PARAMETERS_ATTRIBUTE_NAME, localprms.union(basesprms))


class ParametersContainer(metaclass=ParametersContainerMeta):

    # pylint: disable-next=unused-argument
    def __init__(self, *args, parameters, **kwargs):
        self._set_input_parameters(parameters)
        self._post_set_input_parameters()

    def __deepcopy__(self, memodict=None):
        return type(self)(parameters=self.get_instance_parameters())

    def get_instance_parameters(self):
        return {p: getattr(self, p) for p in self.get_cls_parameters() if hasattr(self, p)}

    def call_baseclass_checker(self, baseclass: type, name):
        assert issubclass(type(self), baseclass)
        baseclass_prm: Parameter = getattr(baseclass, name, None)
        assert baseclass_prm
        baseclass_prm.check(self, getattr(self, name))

    @classmethod
    def get_cls_parameters(cls):
        return getattr(cls, CLASS_PARAMETERS_ATTRIBUTE_NAME)

    @classmethod
    def is_cls_parameter_exist(cls, name):
        return name in cls.get_cls_parameters()

    def _set_input_parameters(self, parameters: dict):
        cls = type(self)
        for input_param_name, value in parameters.items():
            assert cls.is_cls_parameter_exist(input_param_name), f"Attempt to set unknown parameter {input_param_name}"
            setattr(self, input_param_name, value)

    def _post_set_input_parameters(self):
        cls = type(self)
        for param_name in cls.get_cls_parameters():
            prm: Parameter = getattr(cls, param_name)
            if prm.is_set(self):
                continue
            assert not prm.required, f"Required parameter not set {prm.name}"
            if prm.default is not Parameter.NO_VAL:
                setattr(self, prm.name, prm.default)


def parameters_init_simplifier(original_init):

    @wraps(original_init)
    def wrapped(self, *args, **kwargs):
        if "parameters" not in kwargs:
            parameters = {k: v for k, v in kwargs.items() if k in self.get_cls_parameters()}
            original_init(self, *args, parameters=parameters, **kwargs)
        else:
            original_init(self, *args, **kwargs)

    return wrapped
