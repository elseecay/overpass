import sqlite3

from typing import Tuple

import pypika

# pylint: disable-next=wildcard-import
from utils.encoding import *
from utils.common import random_bytes, serial_call

from serialization import serialize, deserialize
from crypto.primitives import VarHashShake128

from app.version import VERSION

# pylint: disable-next=wildcard-import
from .raw import *
from .share import StorageError


MANIFEST_TABLE = "manifest"

KEY_COL = "key"
DATA_COL = "data"


class KeyCheckError(StorageError):

    def __init__(self):
        super().__init__("Incorrect database key")


def init_manifest_table(connection, mixer, key_hasher, hs_hasher):
    _create_minifest_table(connection)
    _insert_app_version(connection)
    _insert_dbid(connection)
    _insert_mixer(connection, mixer)
    _insert_key_hasher(connection, key_hasher)
    _insert_hs_hasher(connection, hs_hasher)
    _insert_key_check(connection, mixer)


def check_key(connection, mixer):
    crypted_check_bytes, iv, check_bytes_hash = get_key_check_data(connection)
    mixer = mixer.opp
    mixer.iv_set(iv)
    check_bytes = mixer.process(crypted_check_bytes)
    check_bytes_hash_calculated = VarHashShake128(digest_size=16).process(check_bytes)
    if check_bytes_hash_calculated != check_bytes_hash:
        raise KeyCheckError()


def get_key_check_data(connection):
    crypted_check_bytes = decode_base64(get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "key_check")[DATA_COL])
    iv = decode_base64(get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "iv_key_check")[DATA_COL])
    check_bytes_hash = decode_base64(get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "shake128_key_check")[DATA_COL])
    return crypted_check_bytes, iv, check_bytes_hash


def is_db_created_by_app(connection):
    try:
        dbid = get_dbid(connection)
    except(sqlite3.Error, StorageError):
        return False
    try:
        dbid = bytes.fromhex(dbid)
    except ValueError:
        return False
    if len(dbid) != 3:
        return False
    return True


def get_mixer(connection):
    row = get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "mixer")
    mixer_decoded = decode_json_base64(row[DATA_COL])
    mixer = deserialize(mixer_decoded)
    return mixer


def get_key_hasher(connection):
    row = get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "key_hasher")
    key_hasher_decoded = decode_json_base64(row[DATA_COL])
    key_hasher = deserialize(key_hasher_decoded)
    return key_hasher


def get_hs_hasher(connection):
    row = get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "hs_hasher")
    hs_hasher_decoded = decode_json_base64(row[DATA_COL])
    hs_hasher = deserialize(hs_hasher_decoded)
    return hs_hasher


def get_app_version(connection) -> Tuple[int, int]:
    version_str = get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "app_version")[KEY_COL]
    major, minor, patch = map(int, version_str.split("."))
    return major, minor, patch


def get_dbid(connection) -> str:
    dbid = get_record_raw(connection, MANIFEST_TABLE, KEY_COL, "dbid")[DATA_COL]
    return dbid


def set_dbid(connection, new_dbid: str):
    try:
        new_dbid_bytes = bytes.fromhex(new_dbid)
    except ValueError:
        raise StorageError(f"Expected hexadecimal string, having {new_dbid}") from None
    if len(new_dbid_bytes) != 3:
        raise StorageError("Size of dbid should be 3 bytes")
    update_record_raw(connection, MANIFEST_TABLE, KEY_COL, "dbid", {DATA_COL: new_dbid.upper()})


def _create_minifest_table(connection):
    columns = [pypika.Column(KEY_COL, "TEXT", nullable=False), pypika.Column(DATA_COL, "TEXT", nullable=False)]
    create_table_raw(connection, MANIFEST_TABLE, *columns, primary_key=KEY_COL)


def _insert_mixer(connection, mixer):
    mixer_encoded = serial_call(mixer, serialize, encode_json_base64)
    insert_record_raw(connection, MANIFEST_TABLE, "mixer", mixer_encoded)


def _insert_key_hasher(connection, key_hasher):
    key_hasher_encoded = serial_call(key_hasher, serialize, encode_json_base64)
    insert_record_raw(connection, MANIFEST_TABLE, "key_hasher", key_hasher_encoded)


def _insert_hs_hasher(connection, hs_hasher):
    hs_hasher_encoded = serial_call(hs_hasher, serialize, encode_json_base64)
    insert_record_raw(connection, MANIFEST_TABLE, "hs_hasher", hs_hasher_encoded)


def _insert_app_version(connection):
    insert_record_raw(connection, MANIFEST_TABLE, "app_version", VERSION)


def _insert_key_check(connection, mixer):
    check_bytes = random_bytes(1337)
    check_bytes_hash = VarHashShake128(digest_size=16).process(check_bytes)
    iv = mixer.iv_set_random()
    crypted_check_bytes = mixer.process(check_bytes)
    insert_record_raw(connection, MANIFEST_TABLE, "key_check", encode_base64(crypted_check_bytes))
    insert_record_raw(connection, MANIFEST_TABLE, "iv_key_check", encode_base64(iv))
    insert_record_raw(connection, MANIFEST_TABLE, "shake128_key_check", encode_base64(check_bytes_hash))


def _insert_dbid(connection):
    dbid = random_bytes(3).hex().upper()
    insert_record_raw(connection, MANIFEST_TABLE, "dbid", dbid)
