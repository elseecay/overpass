import argparse
import sys
import os

from pathlib import Path

from app import config
from app.version import VERSION
from app.ui.console import console


def handle_tool_calls(args):
    if args.get_token_dropbox:
        import main_helpers.token_dropbox
        main_helpers.token_dropbox.get()
        sys.exit(0)
    if args.get_token_yandex:
        import main_helpers.token_yandex
        main_helpers.token_yandex.get()
        sys.exit(0)
    if args.version:
        print(VERSION)
        sys.exit(0)


def handle_test_call(args):
    if args.test:
        import main_helpers.testing
        err_count = main_helpers.testing.run(args)
        if err_count > 0:
            sys.exit(1)
        sys.exit(0)


def read_config(args):
    try:
        if args.config is not None:
            cfg_path = Path(args.config)
        elif "python" in Path(sys.executable).name.lower():
            cfg_path = Path(Path.home(), config.DEV_CONFIG_PATH)
        else:
            cfg_path = Path(Path.home(), config.DEFAULT_CONFIG_PATH)
        if cfg_path.exists():
            cfg = config.read_config(cfg_path)
        else:
            if not args.test:
                print(f"Config file not exist, path: {cfg_path}")
                sys.exit(1)
            db_dir = Path(os.getcwd(), "__databases__")
            cfg = config.create_minimal_config(db_dir)
            cfg_path = "MINIMAL"
        config.set_config(cfg)
        print(f"Config path: {cfg_path}")
    except config.ConfigError as e:
        print(e)
        sys.exit(1)


def process_cmdline_args(args):
    if not args.test:
        return
    for pattern in args.test:
        if pattern == "all":
            args.test[0] = "test"
            break


def get_cmdline_args():
    parser = argparse.ArgumentParser(description="Overpass - pure python password manager")
    parser.add_argument("--config", type=str, help="Set config file path")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--get-token-dropbox", action="store_true", help="Get dropbox refresh token")
    parser.add_argument("--get-token-yandex", action="store_true", help="Get yandex.disk access token")
    parser.add_argument("--test", "-t", type=str, action="append", help=argparse.SUPPRESS)
    args = parser.parse_args()
    return args


def main():
    args = get_cmdline_args()
    process_cmdline_args(args)
    handle_tool_calls(args)
    read_config(args)
    handle_test_call(args)
    console.console_run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
