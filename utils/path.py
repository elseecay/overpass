import os
import shutil

from pathlib import Path


__all__ = [
    "make_existing_file_path",
    "make_existing_dir_path",
    "make_not_existing_path",
    "make_dir_path",
    "make_clean_dir_path",
    "remove_file_path",
    "remove_dir_path"
]


def make_existing_file_path(*args):
    path = Path(*args)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Expected file {path}")
    return path


def make_existing_dir_path(*args):
    path = Path(*args)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist {path}")
    if not path.is_dir():
        raise FileNotFoundError(f"Expected directory {path}")
    return path


def make_not_existing_path(*args):
    path = Path(*args)
    if path.exists():
        raise FileExistsError(f"Path {path} already exist")
    return path


def make_dir_path(*args):
    path = Path(*args)
    if path.exists():
        if path.is_dir():
            return path
        raise FileExistsError(f"Expected directory {path}")
    path.mkdir(parents=True)
    return path


def make_clean_dir_path(*args):
    path = Path(*args)
    if path.exists():
        if not path.is_dir():
            raise FileExistsError(f"Expected directory {path}")
        shutil.rmtree(path, ignore_errors=False, onerror=None)
    path.mkdir(parents=True)
    return path


def remove_file_path(*args):
    path = Path(*args)
    if not path.exists():
        return
    if not path.is_file():
        raise FileExistsError(f"Expected file {path}")
    os.remove(path)


def remove_dir_path(*args):
    path = Path(*args)
    if not path.exists():
        return
    if not path.is_dir():
        raise FileExistsError(f"Expected directory {path}")
    shutil.rmtree(path, ignore_errors=False, onerror=None)
