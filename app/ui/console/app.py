import os
import random
import string
import sys
import secrets

from typing import Optional
from collections import OrderedDict
from functools import wraps
from pathlib import Path
from dataclasses import dataclass, field
from contextlib import closing
from enum import Enum

import prompt_toolkit as ptk

import pyperclip

from utils.encoding import encode_utf8
from utils.common import random_bytes, CloseOnError
from utils.path import make_existing_file_path, remove_file_path
from utils.smrtexcp import SmartException

from crypto import primitives
from crypto.mixer import Mixer, KeyHasher, Hasher

from app import config

from app.ui.console.app_meta import AppStateMeta

from app.cloud import cloud
from app.cloud.share import CloudError

# pylint: disable=unused-import
from app.storage import sql
import app.storage.sql.content
import app.storage.sql.manifest
import app.storage.sql.description
import app.storage.sql.share
import app.storage.sql.impexp
import app.storage.sql.raw
# pylint: enable=unused-import


class Section(Enum):
    DATABASE = "Database"
    TABLE = "Table"
    DATA = "Data"
    CLOUD = "Cloud"
    IMEXP = "Import/Export"
    UTIL = "Utility"
    OTHER = "Other"
    HELPEXIT = "Help/Exit"


@dataclass
class HelpInfo:
    section: str = None
    desc: str = None
    argdesc: dict = field(default_factory=dict)


@dataclass
class CmdInfo:
    con_required: bool = None
    helpinfo: HelpInfo = field(default_factory=HelpInfo)


# pylint: disable-next=too-few-public-methods
class Arg:

    def __init__(self, name: str, desc: str):
        self.name, self.desc = name, desc

    def __call__(self, cmd_callable):
        cmd_callable.cmdinfo.helpinfo.argdesc[self.name] = self.desc
        return cmd_callable


# pylint: disable-next=too-few-public-methods
class Help:

    def __init__(self, section: Section, desc: str):
        self.section, self.desc = section, desc

    def __call__(self, cmd_callable):
        cmd_callable.cmdinfo.helpinfo.section = self.section
        cmd_callable.cmdinfo.helpinfo.desc = self.desc
        return cmd_callable


# pylint: disable-next=too-few-public-methods
class Command:

    def __init__(self, con_required=False):
        self.cmdinfo = CmdInfo(con_required)

    def __call__(self, cmd_callable):

        @wraps(cmd_callable)
        def wrapper(app_state, *args, **kwargs):
            con_required = wrapper.cmdinfo.con_required
            if con_required and not app_state.con_info.is_connected():
                raise AppError("Command requires connection")
            return cmd_callable(app_state, *args, **kwargs)

        wrapper.cmdinfo = self.cmdinfo
        return wrapper


class AppError(SmartException):
    pass


# TODO: catch StorageErrors and reraise AppError?


@dataclass(frozen=True)
class ConnectionInfo:
    ctx: sql.share.ConnectionContext = None
    connection_path: Path = None
    connection_abs_path: Path = None

    def is_connected(self):
        return self.ctx is not None


# pylint: disable-next=too-many-public-methods
class AppState(metaclass=AppStateMeta):

    def __init__(self):
        self.con_info = ConnectionInfo()
        self.cloud = {}

    def __del__(self):
        if self.con_info.is_connected():
            self.con_info.ctx.connection.close()

    @Arg("rewrite", "Remove exsiting file")
    @Arg("connect", "Connect after creation")
    @Help(Section.DATABASE, "Create new database")
    @Command()
    def cmd_newdb(self, path, *, rewrite=False, connect=False):
        path = get_database_absolute_path(path)
        if not rewrite and path.exists():
            raise AppError("Database file already exist, use --rewrite")
        password = _prompt_hidden_input(f"New DB password ({path.name})")
        self.cmd_newdb_backend(path, rewrite=rewrite, connect=connect, password=password)

    @Help(Section.DATABASE, "Delete database")
    @Command()
    def cmd_deldb(self, path):
        path = get_database_absolute_path(path, check_exist=True)
        prompt_res = _prompt_yes_no("Are you sure?")
        if not prompt_res:
            return
        prompt_res = _prompt_yes_no("Are you REALLY sure?")
        if not prompt_res:
            return
        self.cmd_deldb_backend(path)

    @Help(Section.DATABASE, "Connect database")
    @Command()
    def cmd_con(self, path):
        if not get_database_absolute_path(path).exists():
            raise AppError("Database file not exist")
        password = _prompt_hidden_input("Password")
        self.cmd_con_backend(path, password=password)

    @Help(Section.DATABASE, "Disconnect database")
    @Command()
    def cmd_discon(self):
        con_info = self.con_info
        if not con_info.is_connected():
            print("Not connected")
            return
        changed_rows = sql.raw.get_changed_rows_count(con_info.ctx.connection)
        self.cmd_discon_backend()
        print("Disconnected")
        cfg = config.curconfig
        if cfg.cloud.enabled and cfg.cloud.autoupload and changed_rows > 0:
            _disconnect_task_upload(self, con_info.connection_path)

    @Help(Section.DATABASE, "Check current connection")
    @Command()
    def cmd_coninfo(self):
        connection_path = self.cmd_coninfo_backend()
        if connection_path:
            print("Connected to", connection_path)
        else:
            print("Not connected")

    @Arg("attrib", "Get only this attrbute")
    @Arg("clip", "Copy selected attribute to clipboad")
    @Help(Section.DATA, "Get row data by key")
    @Command(con_required=True)
    def cmd_get(self, table, key, /, *, attrib=None, clip=False):
        row = self.cmd_get_backend(table, key)
        if row is None:
            print("No such key")
            return
        if attrib is None:
            for k, v in row.items():
                print(k + ":", v)
        else:
            value = row.get(attrib, None)
            if value is None:
                print("No such attribute")
                return
            _print_or_clip(clip, cdata=value, pdata=f"{attrib}: {value}")

    @Arg("attribs", "name:value pairs")
    @Help(Section.DATA, "Insert new row")
    @Command(con_required=True)
    def cmd_ins(self, table, key, *attribs):
        self.cmd_ins_backend(table, key, *attribs)

    @Arg("attribs", "name:value pairs")
    @Arg("replace", "Remove old data")
    @Arg("new_key", "Set new key")
    @Help(Section.DATA, "Update data by key")
    @Command(con_required=True)
    def cmd_upd(self, table, key, *attribs, replace=False, new_key=None):
        self.cmd_upd_backend(table, key, *attribs, replace=replace, new_key=new_key)

    @Help(Section.DATA, "Delete row by key")
    @Command(con_required=True)
    def cmd_del(self, table, key):
        self.cmd_del_backend(table, key)

    @Help(Section.DATA, "Count table rows")
    @Command(con_required=True)
    def cmd_count(self, table):
        result = self.cmd_count_backend(table)
        print(result)

    @Help(Section.DATA, "Get all table keys")
    @Command(con_required=True)
    def cmd_keys(self, table):
        for k in self.cmd_keys_backend(table):
            print(k)

    @Help(Section.DATA, "Find key by substring")
    @Command(con_required=True)
    def cmd_find(self, table, key_substr):
        for k in self.cmd_find_backend(table, key_substr):
            print(k)

    @Arg("hash_search", "Enable key search by hash")
    @Help(Section.TABLE, "Create new table")
    @Command(con_required=True)
    def cmd_newtable(self, name, *, hash_search=False):
        self.cmd_newtable_backend(name, hash_search=hash_search)

    @Help(Section.TABLE, "Delete table by name")
    @Command(con_required=True)
    def cmd_deltable(self, name):
        self.cmd_deltable_backend(name)

    @Help(Section.TABLE, "Get all tables in database")
    @Command(con_required=True)
    def cmd_tables(self):
        for desc in self.cmd_tables_backend():
            print(desc.name)

    @Help(Section.TABLE, "Get some data about table")
    @Command(con_required=True)
    def cmd_desctable(self, table):
        desc = self.cmd_desctable_backend(table)
        print("name:", desc.name)
        print("rawname:", desc.raw_name)
        print("hs:", desc.hash_search_enabled)

    @Arg("service", "Cloud service name e.g. 'dropbox'")
    @Help(Section.CLOUD, "Upload database to cloud")
    @Command()
    def cmd_cloudup(self, path, *, service=None):
        self.cmd_cloudup_backend(path, service=service)

    @Arg("tables", "List of tables for export")
    @Arg("rewrite", "Rewrite dump file")
    @Arg("all", "Export all tables")
    @Help(Section.IMEXP, "Create decrypted dump")
    @Command(con_required=True)
    def cmd_export(self, path, *tables, rewrite=False, all=False): # pylint: disable=redefined-builtin
        self.cmd_export_backend(path, *tables, rewrite=rewrite, all=all)

    @Arg("tables", "List of tables for import")
    @Arg("all", "Import all tables")
    @Help(Section.IMEXP, "Import from decrypted dump")
    @Command(con_required=True)
    def cmd_import(self, path, *tables, all=False): # pylint: disable=redefined-builtin
        self.cmd_import_backend(path, *tables, all=all)

    @Help(Section.IMEXP, "Get tables list from decrypted dump")
    @Command()
    def cmd_lsdump(self, path):
        connection_dump = sql.raw.db_connect(path)
        tables = sql.raw.get_db_tables_raw(connection_dump)
        for table in tables:
            if table.startswith(sql.content.DUMP_TABLE_PREFIX):
                print(table[len(sql.content.DUMP_TABLE_PREFIX):])

    @Help(Section.UTIL, "Get config entry value")
    @Command()
    def cmd_config(self, entry_path):
        val = config.curconfig.get_entry(entry_path)
        if isinstance(val, config.ConfigEntry):
            print("Config entry")
        else:
            print(val)

    @Arg("clip", "Copy to clipboard")
    @Arg("size", "Password length, default=20")
    @Arg("disable_spec_char", "Do not generate special characters")
    @Help(Section.UTIL, "Generate password")
    @Command()
    def cmd_genpass(self, *, clip=False, size=20, disable_spec_char=False):
        if size < 10:
            print("Too short password")
            return
        password = _gen_password(size, disable_spec_char)
        _print_or_clip(clip, cdata=password, pdata=password)

    @Help(Section.UTIL, "List all databases from config's db_directory")
    @Command()
    def cmd_lsdb(self):
        db_directory = config.curconfig.db_directory
        for root, _, files in os.walk(db_directory):
            for f in files:
                fullpath = Path(root, f)
                relative = fullpath.relative_to(db_directory)
                print(relative)

    @Help(Section.UTIL, "Get database size in MiB")
    @Command()
    def cmd_dbsize(self, path):
        path = get_database_absolute_path(path)
        try:
            path = make_existing_file_path(path)
        except FileNotFoundError as e:
            print(e)
            return
        stat = os.stat(path)
        print(f"{(stat.st_size / 2 ** 20):.2f} MiB")

    @Help(Section.UTIL, "Get current working directory")
    @Command()
    def cmd_pwd(self):
        print(os.getcwd())

    @Help(Section.OTHER, "Get database id")
    @Command(con_required=True)
    def cmd_dbid(self):
        dbid = self.cmd_dbid_backend()
        print(dbid)

    @Arg("new_dbid", "3 bytes hexadecimal string")
    @Help(Section.OTHER, "Set database id")
    @Command(con_required=True)
    def cmd_setdbid(self, new_dbid):
        self.cmd_setdbid_backend(new_dbid)

    @Help(Section.HELPEXIT, "Print available commands")
    @Command()
    def cmd_help(self):
        _print_command_list()

    @Help(Section.HELPEXIT, "Exit")
    @Command()
    def cmd_exit(self):
        try:
            _exit_tasks(self)
        except AppError as e:
            print(e)
        sys.exit(0)

    @Help(Section.HELPEXIT, "Exit")
    @Command()
    def cmd_quit(self):
        return self.cmd_exit()

    @Help(Section.HELPEXIT, "Exit")
    @Command()
    def cmd_q(self):
        return self.cmd_exit()

    def cmd_newdb_backend(self, path, *, rewrite=False, connect=False, password):
        mixer = create_default_mixer()
        key_hasher = create_default_key_hasher()
        _set_mixer_keys(mixer, key_hasher, encode_utf8(password))
        hs_hasher = create_default_hash_search_hasher()
        path = get_database_absolute_path(path)
        connection = sql.raw.db_create_new(path, rewrite=rewrite, connect=True)
        with closing(connection), connection:
            sql.content.init_empty_database(connection, mixer, hs_hasher, key_hasher)
        if connect:
            self.cmd_con_backend(path, password=password)

    def cmd_deldb_backend(self, path):
        path = get_database_absolute_path(path, check_exist=True)
        if self.con_info.connection_abs_path == path:
            raise AppError("Cannot delete currenly connected db")
        try:
            remove_file_path(path)
        except OSError as e:
            raise AppError(original_exception=e) from e

    def cmd_con_backend(self, path, *, password):
        if self.con_info.is_connected():
            self.cmd_discon_backend()
        abs_path = get_database_absolute_path(path)
        password = encode_utf8(password)
        connection = sql.raw.db_connect(abs_path)
        with CloseOnError(connection):
            if not sql.manifest.is_db_created_by_app(connection):
                raise AppError("Database is not created by application")
            hs_hasher = sql.manifest.get_hs_hasher(connection)
            mixer = sql.manifest.get_mixer(connection)
            key_hasher = sql.manifest.get_key_hasher(connection)
            _set_mixer_keys(mixer, key_hasher, password)
            sql.manifest.check_key(connection, mixer)
        rel_path = abs_path.relative_to(config.curconfig.db_directory)
        ctx = sql.share.ConnectionContext(connection, mixer, hs_hasher)
        sql.description.get.cache_clear()
        self.con_info = ConnectionInfo(ctx, rel_path, abs_path)

    def cmd_discon_backend(self):
        con_info = self.con_info
        self.con_info = ConnectionInfo()
        if con_info.is_connected():
            con_info.ctx.connection.close()

    def cmd_coninfo_backend(self):
        return self.con_info.connection_path

    def cmd_get_backend(self, table, key) -> Optional[dict]:
        row = sql.content.get_record(self.con_info.ctx, table, key)
        return row

    def cmd_ins_backend(self, table, key, *attribs):
        attribs = _build_attributes_dict(*attribs)
        with self.con_info.ctx.connection:
            sql.content.insert_record(self.con_info.ctx, table, key, attribs)

    def cmd_upd_backend(self, table, key, *attribs, replace=False, new_key=None):
        attribs = _build_attributes_dict(*attribs)
        with self.con_info.ctx.connection:
            sql.content.update_record(self.con_info.ctx, table, key, attribs, new_key=new_key, replace=replace)

    def cmd_del_backend(self, table, key):
        with self.con_info.ctx.connection:
            sql.content.del_record(self.con_info.ctx, table, key)

    def cmd_count_backend(self, table):
        result = sql.content.count_records(self.con_info.ctx, table)
        return result

    def cmd_keys_backend(self, table):
        row_gen = sql.content.iterate_with_decryption(self.con_info.ctx, table, columns=(sql.content.KEY_COL,))
        return list(row[sql.content.KEY_COL] for row in row_gen)

    def cmd_find_backend(self, table, key_substr):
        row_gen = sql.content.iterate_with_decryption(self.con_info.ctx, table, columns=(sql.content.KEY_COL,))
        key_list = [row[sql.content.KEY_COL] for row in row_gen if key_substr in row[sql.content.KEY_COL]]
        return key_list

    def cmd_newtable_backend(self, name, *, hash_search=False):
        with self.con_info.ctx.connection:
            sql.content.create_table(self.con_info.ctx, name, enable_hash_search=hash_search)

    def cmd_deltable_backend(self, name):
        with self.con_info.ctx.connection:
            sql.content.delete_table(self.con_info.ctx, name)

    def cmd_tables_backend(self):
        return list(sql.description.iterate_with_decryption(self.con_info.ctx))

    def cmd_desctable_backend(self, table):
        desc = sql.description.get(self.con_info.ctx, table)
        return desc

    def cmd_export_backend(self, path, *tables, rewrite=False, all=False): # pylint: disable=redefined-builtin
        sql.impexp.export_tables(self.con_info.ctx, Path(path), *tables, rewrite=rewrite, all=all)

    def cmd_import_backend(self, path, *tables, all=False): # pylint: disable=redefined-builtin
        with self.con_info.ctx.connection:
            sql.impexp.import_tables(self.con_info.ctx, Path(path), *tables, all=all)

    def cmd_cloudup_backend(self, path, *, service=None):
        path = get_database_absolute_path(path, check_exist=True)
        if self.con_info.connection_abs_path == path:
            raise AppError("Cannot upload currenly connected db")
        if not config.curconfig.get_entry("cloud/enabled"):
            raise AppError("Cloud service disabled")
        if service is None:
            service = config.curconfig.cloud.service
        try:
            if self.cloud.get(service, None) is None:
                self.cloud[service] = cloud.init_cloud(service)
            self.cloud[service].upload_database(path)
        except CloudError as e:
            raise AppError(original_exception=e) from None

    def cmd_dbid_backend(self):
        return sql.manifest.get_dbid(self.con_info.ctx.connection)

    def cmd_setdbid_backend(self, new_dbid):
        with self.con_info.ctx.connection:
            sql.manifest.set_dbid(self.con_info.ctx.connection, new_dbid)


def get_database_absolute_path(path, check_exist=False):
    path = Path(path)
    if not path.is_absolute():
        path = Path(config.curconfig.db_directory, path).resolve().absolute()
    if not path.is_relative_to(config.curconfig.db_directory):
        raise AppError("Invalid database path")
    if check_exist:
        try:
            path = make_existing_file_path(path)
        except FileNotFoundError as e:
            raise AppError(original_exception=e) from e
    return path


def create_default_mixer():
    aes = primitives.Enc256AESCTR()
    chacha = primitives.Enc256CHACHA()
    return Mixer(aes, chacha)


def create_default_key_hasher():
    scrypt1 = primitives.Hash256Scrypt(salt=secrets.token_bytes(16), n=2**20, r=2)
    scrypt2 = primitives.Hash256Scrypt(salt=secrets.token_bytes(16), n=2**16, r=32)
    return KeyHasher(scrypt1, scrypt2)


def create_default_hash_search_hasher():
    sha3 = primitives.Hash512SHA3()
    blake = primitives.Hash512BLAKE2()
    big_hasher = Hasher(sha3, blake, iterations=5)
    shake = primitives.VarHashShake128(digest_size=16)
    return Hasher(big_hasher, shake, iterations=1)


def _set_mixer_keys(mixer, key_hasher, password: bytes):
    keys = key_hasher.process(password)
    mixer.set_keys(*keys)
    mixer.opposite_instance(set_attribute=True)


def _gen_password(size=20, disable_spec_char=False):
    # pylint: disable-next=invalid-name
    SPECIAL_CHARACTERS = "()[]{}_!#$%&+-*/<=>?@^~"
    password = []
    alphabet = string.ascii_lowercase + string.ascii_uppercase + string.digits * 2
    password.append(secrets.choice(string.ascii_lowercase))
    password.append(secrets.choice(string.ascii_uppercase))
    password.append(secrets.choice(string.digits))
    if not disable_spec_char:
        alphabet += SPECIAL_CHARACTERS
        password.append(secrets.choice(SPECIAL_CHARACTERS))
    for byte in random_bytes(size - len(password)):
        password.append(alphabet[byte % len(alphabet)])
    random.shuffle(password)
    return "".join(password)


def _prompt_hidden_input(prompt_message) -> str:
    user_input = ptk.prompt(f"{prompt_message}: ", is_password=True)
    return user_input


def _prompt_yes_no(prompt_message) -> bool:
    match ptk.prompt(f"{prompt_message} (y/n): ").lower():
        case "y" | "yes":
            return True
        case "n" | "no":
            return False
        case _:
            raise AppError("Bad input")


def _build_attributes_dict(*attrib_strs: str):
    values = {}
    for attrib_str in attrib_strs:
        name, value = _process_input_attribute(attrib_str)
        if name in values:
            raise AppError(f"Duplicate attribute {name}")
        values[name] = value
    return values


def _process_input_attribute(s: str):
    splitted = s.split(":", 1)
    if len(splitted) != 2:
        raise AppError(f"Invalid attribute string '{s}'")
    name, value = splitted[0], splitted[1]
    value = _process_input_attribute_value(value)
    return name, value


def _process_input_attribute_value(value: str):
    if value.startswith("file="):
        path = Path(value.replace("file=", "", 1))
        try:
            with open(path, "r", encoding="utf-8") as f:
                value = f.read()
        except OSError as e:
            raise AppError(f"Cannot read value file {path}", original_exception=e) from e
    return value


def _disconnect_task_upload(app_state, connection_path):
    print(f"Uploading {connection_path} to {config.curconfig.cloud.service}...")
    app_state.cmd_cloudup_backend(connection_path)
    print("File uploaded")


def _exit_tasks(app_state):
    if app_state.con_info.is_connected():
        _exit_task_disconnect(app_state)


def _exit_task_disconnect(app_state):
    print("Closing current connection...")
    app_state.cmd_discon()


def _print_or_clip(clip: bool, *, cdata=None, pdata=None):
    if clip:
        assert cdata is not None
        pyperclip.copy(cdata)
    else:
        assert pdata is not None
        print(pdata)


def _print_command_list():
    section_dict = OrderedDict((section.value, []) for section in Section)
    for cmd_name in AppState.COMMANDS:
        cmd_callable = getattr(AppState, f"cmd_{cmd_name}")
        section = cmd_callable.cmdinfo.helpinfo.section
        section_dict[section.value].append(cmd_name)
    section_dict.pop(Section.HELPEXIT.value)
    for section, cmd_list in section_dict.items():
        print(section,  ":", sep="")
        for cmd_name in cmd_list:
            print(" " * 2, "- ", cmd_name, sep="")
