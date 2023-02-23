import json

from typing import List, Tuple, Union
from pathlib import Path
from dataclasses import dataclass

from utils.smrtexcp import SmartException


# (main.py) Config path if command was python3 main.py...
DEV_CONFIG_PATH = Path(".overpass-dev", "config.json")


DEFAULT_CONFIG_PATH = Path(".overpass", "config.json")


ADDITIONAL_TYPES_MAP = {
    Path: str
}


class ConfigError(SmartException):
    pass


class ConfigEntry:

    def get_entry(self, entry_path: Union[List, Tuple, str]):
        if isinstance(entry_path, str):
            entry_path = entry_path.split(".")
        assert len(entry_path) >= 1
        entry_name = entry_path[0]
        entry_value = getattr(self, entry_name, None)
        if entry_value is None:
            return None
        if len(entry_path) == 1:
            return entry_value
        if not isinstance(entry_value, ConfigEntry):
            return None
        return entry_value.get_entry(entry_path[1:])

    def set_entry(self, entry_value, entry_path: Union[List, Tuple, str], *, full_entry_path: str = None):
        if isinstance(entry_path, str):
            entry_path = entry_path.split(".")
        if full_entry_path is None:
            full_entry_path = ".".join(entry_path)
        assert len(entry_path) >= 1
        entry_name = entry_path[0]
        if entry_name not in type(self).__annotations__:
            raise ConfigError(f"Unexpected entry '{entry_name}', path: {full_entry_path}")
        annotation_cls = type(self).__annotations__[entry_name]
        if len(entry_path) == 1:
            if issubclass(annotation_cls, ConfigEntry):
                raise ConfigError(f"Invalid entry path, path is too short, path: {full_entry_path}")
            if isinstance(entry_value, annotation_cls):
                setattr(self, entry_name, entry_value)
            elif annotation_cls in ADDITIONAL_TYPES_MAP and isinstance(entry_value, ADDITIONAL_TYPES_MAP[annotation_cls]):
                setattr(self, entry_name, annotation_cls(entry_value))
            else:
                raise ConfigError(f"Invalid entry value type, path: {full_entry_path}")
        else:
            if not issubclass(annotation_cls, ConfigEntry):
                raise ConfigError(f"Invalid entry path, path is too long, path: {full_entry_path}")
            if getattr(self, entry_name, None) is None:
                setattr(self, entry_name, annotation_cls())
            getattr(self, entry_name).set_entry(entry_value, entry_path[1:], full_entry_path=full_entry_path)

    def check(self):
        pass


@dataclass(init=False)
class Dropbox(ConfigEntry):
    upload_directory: str = None
    refresh_token_path: Path = None

    def check(self):
        if not Path(self.refresh_token_path).exists():
            raise ConfigError("Dropbox refresh token path not exist")
        if not self.upload_directory.startswith("/"):
            raise ConfigError("Upload directory should start with /")
        if not self.upload_directory.endswith("/"):
            raise ConfigError("Upload directory should end with /")


@dataclass(init=False)
class YandexDisk(ConfigEntry):
    upload_directory: str = None
    access_token_path: Path = None

    def check(self):
        if not Path(self.access_token_path).exists():
            raise ConfigError("Yandex access token path not exist")
        if not self.upload_directory.startswith("app:/"):
            raise ConfigError("Upload directory should start with app:/")
        if not self.upload_directory.endswith("/"):
            raise ConfigError("Upload directory should end with /")


SUPPORTED_CLOUD_SERVICES = ["dropbox", "yandex_disk"]


@dataclass(init=False)
class Cloud(ConfigEntry):
    enabled: bool = None
    service: str = None
    autoupload: bool = None

    dropbox: Dropbox = None
    yandex_disk: YandexDisk = None

    def check(self):
        if not self.enabled:
            return
        if not self.service:
            raise ConfigError("Cloud service name not set")
        if self.service not in SUPPORTED_CLOUD_SERVICES:
            raise ConfigError(f"Not supported cloud service '{self.service}'")
        service_config = self.get_entry(self.service)
        if service_config is None:
            raise ConfigError(f"Cloud service '{self.service}' not configured")
        service_config.check()


@dataclass(init=False)
class Config(ConfigEntry):
    config_path: Path = None
    db_directory: Path = None
    default_db: Path = None
    cloud: Cloud = None

    def check(self):
        if self.db_directory is None:
            raise ConfigError("db_directory not set")
        if not self.db_directory.is_absolute():
            raise ConfigError("db_directory should be an absolute path")
        if not self.db_directory.exists():
            raise ConfigError("db_directory path not exist")
        if self.cloud is not None:
            self.cloud.check()

    def fill(self, keys, *, path=None):
        if path is None:
            path = []
        for name, value in keys.items():
            path.append(name)
            if isinstance(value, dict):
                self.fill(value, path=path)
            else:
                self.set_entry(value, path)
            path.pop(-1)


curconfig: Config = None


def create_minimal_config(db_directory):
    cfg = Config()
    cfg.set_entry(Path(db_directory), "db_directory")
    return cfg


def read_config(path=None) -> Config:
    if path is None:
        path = Path(Path.home(), DEFAULT_CONFIG_PATH)
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as fd:
            file_content = fd.read()
    except OSError as e:
        raise ConfigError(f"Cannot read config file, path: {path}", original_exception=e) from e
    try:
        keys = json.loads(file_content)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file is invalid json, path: {path}", original_exception=e) from e
    cfg = Config()
    cfg.config_path = path
    cfg.fill(keys)
    cfg.check()
    return cfg


def set_config(config: Config):
    # pylint: disable-next=global-statement,invalid-name
    global curconfig
    curconfig = config
