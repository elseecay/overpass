from time import perf_counter_ns

# pylint: disable=unused-import

import prompt_toolkit as ptk
import prompt_toolkit.history
import prompt_toolkit.lexers
import prompt_toolkit.styles.pygments
import prompt_toolkit.completion
import prompt_toolkit.formatted_text

import pygments as pyg
import pygments.lexer
import pygments.styles
import pygments.token

from utils.smrtexcp import SmartException

from app import config
from app.storage.sql.share import StorageError
from app.storage.sql.manifest import KeyCheckError

from .app import AppState, AppError
from .app_meta import call_command_from_cmdline_args


class CmdlineLexer(pyg.lexer.RegexLexer):

    tokens = {
        'root': [
            (r"^[\w]+", pyg.token.Keyword),
            (r"--[a-z0-9-]+", pyg.token.Comment),
            (r"-[a-zA-Z0-9]", pyg.token.Comment),
            (r'"(.| )*"', pyg.token.String),
            (r" ", pyg.token.Text),
            (r"[^ ]+", pyg.token.Text),
        ]
    }


class FirstWordCompleter(ptk.completion.WordCompleter):

    def get_completions(self, document, complete_event):
        if len(document.text.split(" ")) != 1:
            return
        yield from super().get_completions(document, complete_event)


def get_prompt_parameters():
    result = {}
    result["completer"] = FirstWordCompleter(list(AppState.COMMANDS))
    result["lexer"] = ptk.lexers.PygmentsLexer(CmdlineLexer)
    result["history"] = ptk.history.InMemoryHistory()
    result["style"] = ptk.styles.pygments.style_from_pygments_cls(pyg.styles.get_style_by_name("inkpot"))
    result["include_default_pygments_style"] = False
    return result


class EmptyCommand(Exception):
    pass


class InvalidCommand(SmartException):
    pass


def build_strings_list(cmd: str):
    strings = ['']
    state_parse_string = False
    for char in cmd:
        if state_parse_string:
            if char == "\"":
                state_parse_string = False
            else:
                strings[-1] += char
        else:
            if char == " ":
                strings.append('')
            elif char == "\"":
                state_parse_string = True
            else:
                strings[-1] += char
    strings = [val for val in strings if len(val) > 0]
    if state_parse_string:
        raise InvalidCommand("Unterminated string literal")
    return strings


def build_argv(cmd: str):
    cmd = cmd.strip(" ")
    strings_list = build_strings_list(cmd)
    return strings_list


def extract_callable_and_args(cmd: str):
    argv = build_argv(cmd)
    if len(argv) == 0:
        raise EmptyCommand()
    cmd_name = argv[0]
    if cmd_name not in AppState.COMMANDS:
        raise InvalidCommand("Unknown command, use 'help' for command list")
    cmd_callable = getattr(AppState, f"cmd_{cmd_name}")
    try:
        args = cmd_callable.argparser.parse_args(argv[1:])
    except SystemExit:
        # NOTE: argparse bug, SystemExit on error or --help
        if "-h" in argv or "--help" in argv:
            raise EmptyCommand() from None
        raise InvalidCommand("Try again") from None
    return cmd_callable, args


EXEC_SUCCESS = 0x00
EXEC_FAILED = 0x01


def execute_command(app_state, cmd: str) -> int:
    try:
        cmd_callable, args = extract_callable_and_args(cmd)
    except EmptyCommand:
        return EXEC_SUCCESS
    except InvalidCommand as e:
        print(e)
        return EXEC_FAILED
    try:
        begin = perf_counter_ns()
        call_command_from_cmdline_args(app_state, cmd_callable, args)
        end = perf_counter_ns()
        print("#>", int((end - begin) / 10**6), "ms")
    # TODO: catch only AppError?
    except (AppError, StorageError) as e:
        print(e)
        return EXEC_FAILED
    return EXEC_SUCCESS


def console_run():
    app_state = AppState()
    _connect_default_db(app_state)
    last_exec_status = EXEC_SUCCESS
    prompt_parameters = get_prompt_parameters()
    while True:
        angle_brackets_color = "#00ff00" if last_exec_status is EXEC_SUCCESS else "#ffffff"
        angle_brackets = ptk.formatted_text.FormattedText([(angle_brackets_color, ">> ")])
        cmd = ptk.prompt(angle_brackets, **prompt_parameters)
        last_exec_status = execute_command(app_state, cmd)


def _connect_default_db(app_state):
    if not config.curconfig.default_db:
        return
    print("Default database:", config.curconfig.default_db)
    while True:
        try:
            app_state.cmd_con(config.curconfig.default_db)
        except KeyCheckError:
            print("Incorrect password")
            continue
        except (AppError, StorageError) as e:
            print(e)
        return
