from functools import lru_cache
from typing import Iterable, Optional
from dataclasses import dataclass, astuple
from collections import namedtuple

import pypika

# pylint: disable-next=wildcard-import
from utils.encoding import *
from utils.common import serial_call

from crypto.tools import encode_add_padding, decode_add_padding

from serialization import serialize, deserialize

from .share import StorageError

# pylint: disable-next=wildcard-import
from .raw import *


DESCRIPTION_TABLE = "description"
IV_DESCRIPTION_TABLE = "iv_description"

DUMP_TABLE_NAME = "description"

KEY_COL = "key"
DATA_COL = "data"

IV_DATA_COL = "iv_data"

MIN_DESC_PAD_SIZE = 100
MAX_DESC_PAD_RND_SIZE = 20

DescEncryptionResult = namedtuple("DescEncryptionResult", ["iv", "crypted_data"])


@dataclass
class TableDescription:
    raw_name: str
    name: str
    hash_search_enabled: bool
    iv_name: str = None
    hs_name: str = None
    hs_data: bytes = None


class TableNotExist(StorageError):

    def __init__(self, table_name):
        super().__init__(f"No such table '{table_name}'")
        self.table_name = table_name


def init_description_table(connection):
    columns = [pypika.Column("key", "TEXT", nullable=False), pypika.Column("data", "TEXT", nullable=False)]
    create_table_raw(connection, DESCRIPTION_TABLE, *columns, primary_key=KEY_COL)
    columns = [pypika.Column("key", "TEXT", nullable=False), pypika.Column("iv_data", "TEXT", nullable=False)]
    create_table_raw(connection, IV_DESCRIPTION_TABLE, *columns, primary_key=KEY_COL, foreign_key=ForeignKey("key", "key", DESCRIPTION_TABLE))


def insert(ctx, table_desc: TableDescription):
    iv, crypted_desc = _encrypt_desc(ctx.mixer, table_desc)
    insert_record_raw(ctx.connection, DESCRIPTION_TABLE, table_desc.raw_name, crypted_desc, columns=(KEY_COL, DATA_COL))
    insert_record_raw(ctx.connection, IV_DESCRIPTION_TABLE, table_desc.raw_name, iv, columns=(KEY_COL, IV_DATA_COL))


def delete(ctx, table_name):
    desc = get(ctx, table_name)
    get.cache_clear()
    delete_record_raw(ctx.connection, IV_DESCRIPTION_TABLE, KEY_COL, desc.raw_name)
    delete_record_raw(ctx.connection, DESCRIPTION_TABLE, KEY_COL, desc.raw_name)


@lru_cache(maxsize=16) # NOTE: cache clear in description.delete, cmd_con_backend
def get(ctx, table_name) -> TableDescription:
    for desc in iterate_with_decryption(ctx):
        if table_name == desc.name:
            return desc
    raise TableNotExist(table_name)


def get_unsafe(ctx, table_name) -> Optional[TableDescription]:
    try:
        return get(ctx, table_name)
    except TableNotExist:
        return None


def is_table_exist(ctx, table_name) -> bool:
    return get_unsafe(ctx, table_name) is not None


def iterate_with_decryption(ctx) -> Iterable[TableDescription]:
    sql_text = _build_query_select_joined_iv().get_sql()
    # pylint: disable-next=unnecessary-lambda-assignment
    decrypt_callback = lambda row: _decrypt_desc(ctx.mixer, row)
    yield from iterate_query_raw(ctx.connection, sql_text, callback=decrypt_callback)


def _build_query_select_joined_iv():
    # pylint: disable-next=unbalanced-tuple-unpacking
    table, iv_table = pypika.Tables(DESCRIPTION_TABLE, IV_DESCRIPTION_TABLE)
    query = pypika.Query.from_(table).inner_join(iv_table).on(getattr(table, KEY_COL) == getattr(iv_table, KEY_COL))
    query = query.select(getattr(table, DATA_COL), getattr(iv_table, IV_DATA_COL))
    return query


def _encrypt_desc(mixer, desc: TableDescription) -> DescEncryptionResult:
    iv = encode_base64(mixer.iv_set_random())
    desc = serial_call(desc, astuple, serialize, encode_json, encode_utf8)
    desc = encode_add_padding(desc, MIN_DESC_PAD_SIZE, MAX_DESC_PAD_RND_SIZE)
    crypted_desc = serial_call(desc, mixer.process, encode_base64)
    return DescEncryptionResult(iv, crypted_desc)


def _decrypt_desc(mixer, row) -> TableDescription:
    mixer = mixer.opp
    iv = decode_base64(row[IV_DATA_COL])
    mixer.iv_set(iv)
    tuple_desc = serial_call(row[DATA_COL], decode_base64, mixer.process, decode_add_padding, decode_utf8, decode_json, deserialize)
    return TableDescription(*tuple_desc)
