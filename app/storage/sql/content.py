import collections
import secrets

from typing import Iterable
from collections import namedtuple

import pypika

# pylint: disable-next=wildcard-import
from utils.encoding import *
from utils.common import serial_call

from crypto.primitives import Hash512SHA3
from crypto.tools import encode_add_padding, decode_add_padding

from . import manifest
from . import description

from .description import TableDescription
from .share import StorageError
# pylint: disable-next=wildcard-import
from .raw import *


RAW_TABLE_PREFIX = "table_"
DUMP_TABLE_PREFIX = "content_"

IV_TABLE_PREFIX = "iv_"
HS_TABLE_PREFIX = "hs_"

ID_COL = "id"
KEY_COL = "key"
DATA_COL = "data"

IV_KEY_COL = f"iv_{KEY_COL}"
IV_DATA_COL = f"iv_{DATA_COL}"

HS_HASH_COL = "hs_hash"

MIN_HS_DATA_SIZE = 30
MAX_HS_DATA_SIZE = 60

MIN_KEY_PAD_SIZE = 12
MAX_KEY_PAD_RND_SIZE = 6

MAX_DATA_PAD_RND_SIZE = 6

KeyEncryptionResult = namedtuple("KeyEncryptionResult", ["iv_key", "crypted_key", "key_hash"])
DataEncryptionResult = namedtuple("DataEncryptionResult", ["iv_data", "crypted_data"])


def init_empty_database(connection, mixer, hs_hasher, key_hasher):
    if len(get_db_tables_raw(connection)) > 0:
        raise StorageError("Database is not empty for initializing")
    with connection:
        manifest.init_manifest_table(connection, mixer, key_hasher, hs_hasher)
        description.init_description_table(connection)
    try:
        manifest.check_key(connection, mixer)
    except manifest.KeyCheckError:
        assert False, "Cannot verify key after database initialization, encryption error"


def create_table(ctx, original_table_name, *, enable_hash_search=False):
    if description.is_table_exist(ctx, original_table_name):
        raise StorageError(f"Table '{original_table_name}' already exists")
    counter = _get_free_table_counter(ctx)
    desc = TableDescription(f"{RAW_TABLE_PREFIX}{counter}", original_table_name, enable_hash_search)
    _create_content_table(ctx, desc)
    _create_iv_table(ctx, desc)
    if desc.hash_search_enabled:
        _create_hs_table(ctx, desc)
    description.insert(ctx, desc)


def _get_free_table_counter(ctx) -> str:
    counter_set = set(range(1000))
    for desc in description.iterate_with_decryption(ctx):
        desc_counter = int(desc.raw_name.replace(RAW_TABLE_PREFIX, ""))
        counter_set.remove(desc_counter)
    if len(counter_set) == 0:
        raise StorageError("Tables limit exceeded (1000)")
    return str(counter_set.pop()).zfill(3)


def _create_content_table(ctx, desc):
    columns = [pypika.Column(KEY_COL, "TEXT", nullable=False)]
    columns.append(pypika.Column(DATA_COL, "TEXT", nullable=False))
    columns.append(pypika.Column(ID_COL, "INTEGER", nullable=False))
    create_table_raw(ctx.connection, desc.raw_name, *columns, primary_key=ID_COL)


def _create_iv_table(ctx, desc):
    iv_table_name = f"{IV_TABLE_PREFIX}{desc.raw_name}"
    desc.iv_name = iv_table_name
    columns = [pypika.Column(IV_KEY_COL, "TEXT", nullable=False)]
    columns.append(pypika.Column(IV_DATA_COL, "TEXT", nullable=False))
    columns.append(pypika.Column(ID_COL, "INTEGER", nullable=False))
    create_table_raw(ctx.connection, iv_table_name, *columns, primary_key=ID_COL, foreign_key=ForeignKey(ID_COL, ID_COL, desc.raw_name))


def _create_hs_table(ctx, desc):
    hs_table_name = f"{HS_TABLE_PREFIX}{desc.raw_name}"
    desc.hs_name = hs_table_name
    desc.hs_data = secrets.token_bytes(MIN_HS_DATA_SIZE + secrets.randbelow(MAX_HS_DATA_SIZE - MIN_HS_DATA_SIZE))
    columns = [pypika.Column(HS_HASH_COL, "TEXT", nullable=False)]
    columns.append(pypika.Column(ID_COL, "INTEGER", nullable=False))
    create_table_raw(ctx.connection, hs_table_name, *columns, primary_key=ID_COL, foreign_key=ForeignKey(ID_COL, ID_COL, desc.raw_name), unique=(HS_HASH_COL,))
    create_index_raw(ctx.connection, hs_table_name, HS_HASH_COL)


def delete_table(ctx, table):
    desc = description.get(ctx, table)
    description.delete(ctx, table)
    if desc.hash_search_enabled:
        delete_table_raw(ctx.connection, f"{HS_TABLE_PREFIX}{desc.raw_name}")
    delete_table_raw(ctx.connection, f"{IV_TABLE_PREFIX}{desc.raw_name}")
    delete_table_raw(ctx.connection, desc.raw_name)


def copy_data(ctx, src_table: str, dst_table: str):
    if not description.is_table_exist(ctx, src_table):
        raise StorageError(f"Table {src_table} not exist")
    if not description.is_table_exist(ctx, dst_table):
        raise StorageError(f"Table {dst_table} not exist")
    if count_records(ctx, dst_table) > 0:
        raise StorageError("Copy not allowed to non-empty tables")
    for row in iterate_with_decryption(ctx, src_table):
        key, attribs = row[KEY_COL], row[DATA_COL]
        insert_record(ctx, dst_table, key, attribs)


def insert_record(ctx, table, key: str, attribs: dict):
    desc = description.get(ctx, table)
    record_exist = get_rowid_by_key(ctx, desc, key) is not None
    if record_exist:
        raise StorageError(f"Key '{key}' already exists")
    assert all(isinstance(val, str) for val in attribs.values()), "Values should have string type"
    iv_key, crypted_key, key_hash = encrypt_key(ctx, key, desc)
    iv_data, crypted_data = encrypt_data(ctx, attribs)
    rowid = insert_record_raw(ctx.connection, desc.raw_name, crypted_key, crypted_data, columns=(KEY_COL, DATA_COL), rowid=True)
    insert_record_raw(ctx.connection, f"{IV_TABLE_PREFIX}{desc.raw_name}", iv_key, iv_data, rowid, columns=(IV_KEY_COL, IV_DATA_COL, ID_COL))
    if desc.hash_search_enabled:
        insert_record_raw(ctx.connection, f"{HS_TABLE_PREFIX}{desc.raw_name}", key_hash, rowid, columns=(HS_HASH_COL, ID_COL))


def update_record(ctx, table, key: str, attribs: dict, *, new_key=None, replace=False):
    desc = description.get(ctx, table)
    rowid = get_rowid_by_key(ctx, desc, key)
    if rowid is None:
        raise StorageError(f"Key '{key}' not exist")
    assert all(isinstance(val, str) for val in attribs.values()), "Values should have string type"
    if new_key is not None and get_rowid_by_key(ctx, desc, new_key) is not None:
        raise StorageError(f"Key '{new_key}' already exist")
    if new_key is None:
        new_key = key
    new_data = {} if replace else dict(get_record_by_id(ctx, desc, rowid))
    new_data.update(attribs)
    iv_key, crypted_key, key_hash = encrypt_key(ctx, new_key, desc)
    iv_data, crypted_data = encrypt_data(ctx, new_data)
    update_record_raw(ctx.connection, desc.raw_name, ID_COL, rowid, {KEY_COL: crypted_key, DATA_COL: crypted_data})
    update_record_raw(ctx.connection, desc.iv_name, ID_COL, rowid, {IV_KEY_COL: iv_key, IV_DATA_COL: iv_data})
    if desc.hash_search_enabled:
        update_record_raw(ctx.connection, desc.hs_name, ID_COL, rowid, {HS_HASH_COL: key_hash})


def get_record(ctx, table, key) -> Optional[dict]:
    desc = description.get(ctx, table)
    rowid = get_rowid_by_key(ctx, desc, key)
    if not rowid:
        return None
    return get_record_by_id(ctx, desc, rowid)


def get_encrypted_joined_iv_row(ctx, desc, rowid):
    query = _build_query_select_rowid_joined_iv(desc.raw_name, rowid)
    row = execute_sql(ctx.connection, query.get_sql(), fetch_one=True)
    return row


def get_record_by_id(ctx, desc, rowid):
    row = get_encrypted_joined_iv_row(ctx, desc, rowid)
    row = decrypt_row(ctx.mixer, row)
    return row[DATA_COL]


def del_record(ctx, table, key):
    desc = description.get(ctx, table)
    rowid = get_rowid_by_key(ctx, desc, key)
    if not rowid:
        return None
    return del_record_by_id(ctx, desc, rowid)


def del_record_by_id(ctx, desc, rowid):
    if desc.hash_search_enabled:
        delete_record_raw(ctx.connection, f"{HS_TABLE_PREFIX}{desc.raw_name}", ID_COL, rowid)
    delete_record_raw(ctx.connection, f"{IV_TABLE_PREFIX}{desc.raw_name}", ID_COL, rowid)
    delete_record_raw(ctx.connection, desc.raw_name, ID_COL, rowid)


def count_records(ctx, table):
    desc = description.get(ctx, table)
    return count_star_raw(ctx.connection, desc.raw_name)


# UTILS


def get_rowid_by_key(ctx, desc, key) -> Optional[int]:
    if desc.hash_search_enabled:
        return get_rowid_by_key_hash(ctx, desc, key)
    return get_rowid_by_seq_decryption(ctx, desc, key)


def get_rowid_by_key_hash(ctx, desc, key):
    key_hash = calc_key_hash(ctx.hs_hasher, desc, key)
    hs_row = get_record_raw(ctx.connection, f"{HS_TABLE_PREFIX}{desc.raw_name}", HS_HASH_COL, key_hash)
    if not hs_row:
        return None
    rowid = hs_row[ID_COL]
    return rowid


def get_rowid_by_seq_decryption(ctx, desc, key):
    for row in iterate_with_decryption(ctx, desc.name, columns=(ID_COL, KEY_COL)):
        if row[KEY_COL] == key:
            return row[ID_COL]
    return None


def iterate_with_decryption(ctx, table, *, columns=(STAR,)) -> Iterable[collections.OrderedDict]:
    table_raw_name = description.get(ctx, table).raw_name
    # pylint: disable-next=unnecessary-lambda-assignment
    decrypt_callback = lambda row: decrypt_row(ctx.mixer, row)
    yield from _iterate_table_joined_iv_raw(ctx, table_raw_name, *columns, callback=decrypt_callback)


def _iterate_table_joined_iv_raw(ctx, raw_table_name, *cols, callback=None):
    query = _build_query_select_joined_iv(raw_table_name, *cols)
    yield from iterate_query_raw(ctx.connection, query.get_sql(), callback=callback)


def _build_query_select_joined_iv(raw_table_name, *cols):
    # pylint: disable-next=unbalanced-tuple-unpacking
    raw_table_name, iv_table = pypika.Tables(raw_table_name, f"iv_{raw_table_name}")
    query = pypika.Query.from_(raw_table_name).inner_join(iv_table).on(getattr(raw_table_name, ID_COL) == getattr(iv_table, ID_COL))
    if len(cols) > 1 or cols[0] != STAR:
        cols = (*cols, *(getattr(iv_table, f"iv_{col}") for col in cols if col != ID_COL))
    query = query.select(*cols)
    return query


def _build_query_select_rowid_joined_iv(raw_table_name, rowid):
    # pylint: disable-next=unbalanced-tuple-unpacking
    raw_table_name, iv_table = pypika.Tables(raw_table_name, f"{IV_TABLE_PREFIX}{raw_table_name}")
    query = pypika.Query.from_(raw_table_name).inner_join(iv_table).on(getattr(raw_table_name, ID_COL) == getattr(iv_table, ID_COL))
    query = query.where(getattr(raw_table_name, ID_COL) == rowid)
    query = query.select(STAR)
    return query


def encrypt_key(ctx, key: str, desc: TableDescription) -> KeyEncryptionResult:
    key_hash = calc_key_hash(ctx.hs_hasher, desc, key) if desc.hash_search_enabled else None
    key = encode_utf8(key)
    key = encode_add_padding(key, MIN_KEY_PAD_SIZE, MAX_KEY_PAD_RND_SIZE)
    iv_key = encode_base64(ctx.mixer.iv_set_random())
    crypted_key = serial_call(key, ctx.mixer.process, encode_base64)
    return KeyEncryptionResult(iv_key, crypted_key, key_hash)


def encrypt_data(ctx, data: dict) -> DataEncryptionResult:
    data = serial_call(data, encode_json, encode_utf8)
    data = encode_add_padding(data, 0, MAX_DATA_PAD_RND_SIZE)
    iv_data = encode_base64(ctx.mixer.iv_set_random())
    crypted_data = serial_call(data, ctx.mixer.process, encode_base64)
    return DataEncryptionResult(iv_data, crypted_data)


def decrypt_row(mixer, row) -> collections.OrderedDict:
    result = collections.OrderedDict()
    if KEY_COL in row.keys():
        result[KEY_COL] = decrypt_key_col(mixer, row)
    if DATA_COL in row.keys():
        result[DATA_COL] = decrypt_data_col(mixer, row)
    if ID_COL in row.keys():
        result[ID_COL] = row[ID_COL]
    return result


def decrypt_key_col(mixer, row):
    encrypted_pk = row[KEY_COL]
    key = decrypt_bytes(mixer, encrypted_pk, row[IV_KEY_COL])
    key = decode_add_padding(key)
    key = decode_utf8(key)
    return key


def decrypt_data_col(mixer, row) -> dict:
    encrypted_data = row[DATA_COL]
    data = decrypt_bytes(mixer, encrypted_data, row[IV_DATA_COL])
    data = decode_add_padding(data)
    data = serial_call(data, decode_utf8, decode_json)
    return data


def decrypt_bytes(mixer, encrypted_data_base64: str, iv_base64: str) -> bytes:
    mixer = mixer.opp
    iv = decode_base64(iv_base64)
    mixer.iv_set(iv)
    decrypted_data = serial_call(encrypted_data_base64, decode_base64, mixer.process)
    return decrypted_data


def calc_key_hash(hs_hasher, desc, key: str) -> str:
    key = encode_utf8(key)
    middle_idx = len(desc.hs_data) // 2
    hs_data_fh = desc.hs_data[:middle_idx]
    hs_data_sh = desc.hs_data[middle_idx:]
    part1 = hs_data_fh + key
    part2 = hs_data_sh + (encode_utf8(desc.raw_name) + key + encode_utf8(desc.name))
    hs_hasher_input = Hash512SHA3().process(part1) + Hash512SHA3().process(part2)
    result = encode_base64(hs_hasher.process(hs_hasher_input))
    return result


# EXPORT / IMPORT


def export_table(ctx, connection_dump, table: str):
    if is_table_exist_raw(connection_dump, table):
        raise StorageError(f"Table in dump already exist {table}")
    if not description.is_table_exist(ctx, table):
        raise StorageError(f"Table not exist {table}")
    dump_table_name = f"{DUMP_TABLE_PREFIX}{table}"
    create_table_raw(connection_dump, dump_table_name, KEY_COL, DATA_COL)
    for row in iterate_with_decryption(ctx, table):
        insert_record_raw(connection_dump, dump_table_name, row[KEY_COL], encode_json(row[DATA_COL]))


def import_table(ctx, connection_dump, table: str):
    dump_table_name = f"{DUMP_TABLE_PREFIX}{table}"
    if not is_table_exist_raw(connection_dump, dump_table_name):
        raise StorageError(f"Table in dump not exist {table}")
    if not description.is_table_exist(ctx, table):
        raise StorageError(f"Table not created {table}")
    if count_records(ctx, table) > 0:
        raise StorageError(f"Table is not empty {table}")
    for row in iterate_table_raw(connection_dump, dump_table_name):
        insert_record(ctx, table, row[KEY_COL], decode_json(row[DATA_COL]))
