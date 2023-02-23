import inspect
import argparse

from argparse import ArgumentParser
from inspect import Parameter
from collections import defaultdict
from functools import wraps


def call_command_from_cmdline_args(app_state, cmd_callable, args: argparse.Namespace):
    assert isinstance(args, argparse.Namespace)
    sig = cmd_callable.sig.parameters
    positional_args, keyword_args = [], {}
    for name, param in sig.items():
        if name == "self":
            continue
        value = getattr(args, name)
        if value is None:
            continue
        if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
            positional_args.append(value)
        elif param.kind is Parameter.VAR_POSITIONAL:
            positional_args.extend(value)
        else:
            keyword_args[name] = value
    return cmd_callable(app_state, *positional_args, **keyword_args)


class AppStateMeta(type):

    def __init__(cls, name, bases, attribs):
        super().__init__(name, bases, attribs)
        cls.COMMANDS = tuple(cmd_name[4:] for cmd_name in attribs.keys() if cmd_name.startswith("cmd_") and not cmd_name.endswith("backend"))
        _gen_argparsers(cls)
        _gen_connection_assert_for_backends(cls)


def _gen_argparsers(cls):
    for cmd in cls.COMMANDS:
        cmd_callable = getattr(cls, f"cmd_{cmd}")
        setattr(cmd_callable, "sig", inspect.signature(cmd_callable))
        setattr(cmd_callable, "argparser", _gen_argparser(cmd_callable))


def _gen_connection_assert_for_backends(cls):
    for cmd in cls.COMMANDS:
        cmd_callable = getattr(cls, f"cmd_{cmd}")
        if cmd_callable.cmdinfo.con_required and hasattr(cls, f"cmd_{cmd}_backend"):
            backend_callable = getattr(cls, f"cmd_{cmd}_backend")
            new_backend_callable = _add_connection_assert_for_backend(backend_callable)
            setattr(cls, f"cmd_{cmd}_backend", new_backend_callable)


def _gen_argparser(cmd_callable) -> ArgumentParser:
    helpinfo = cmd_callable.cmdinfo.helpinfo
    parser = ArgumentParser(cmd_callable.__name__[4:], exit_on_error=False, description=helpinfo.desc)
    params = [(name, param) for name, param in cmd_callable.sig.parameters.items() if name != "self"]
    first_char_dict = defaultdict(int)
    for name, _ in params:
        if not name.count("_"):
            first_char_dict[name[0]] += 1
    for name, param in params:
        push_arg_pos, push_arg_kw = [], {}
        if param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD):
            push_arg_pos.append(name)
            push_arg_kw["type"] = str
            push_arg_kw["metavar"] = name
        elif param.kind is Parameter.VAR_POSITIONAL:
            push_arg_pos.append(name)
            push_arg_kw["type"] = str
            push_arg_kw["nargs"] = "*"
            push_arg_kw["metavar"] = name
        elif param.kind is Parameter.KEYWORD_ONLY:
            push_arg_pos.append("--" + name.replace("_", "-"))
            if name.count("_") == 0 and first_char_dict[name[0]] == 1:
                push_arg_pos.append("-" + name[0])
            push_arg_kw["required"] = param.default is Parameter.empty
            if push_arg_kw["required"] or param.default is None:
                push_arg_kw["type"] = str
            else:
                push_arg_kw["type"] = type(param.default)
            if push_arg_kw["type"] is bool:
                assert param.default is False
                push_arg_kw["action"] = "store_true"
                del push_arg_kw["type"]
        else:
            assert False, f"Kwargs not implemented, cmd={parser.prog}"
        push_arg_kw["help"] = helpinfo.argdesc.get(name, None)
        parser.add_argument(*push_arg_pos, **push_arg_kw)
    return parser


def _add_connection_assert_for_backend(backend_callable):

    @wraps(backend_callable)
    def wrapper(app_state, *args, **kwargs):
        assert app_state.con_info.is_connected()
        return backend_callable(app_state, *args, **kwargs)

    return wrapper
