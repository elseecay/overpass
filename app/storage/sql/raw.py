import sqlite3

from typing import List, Optional, Union
from dataclasses import dataclass
from contextlib import closing
from pathlib import Path

import pypika

import utils.common
from utils.path import make_not_existing_path, make_existing_file_path, remove_file_path

from .share import StorageError


@dataclass
class ForeignKey:
    column: str
    ref_column: str
    ref_table: str


STAR = "*"


def db_create_new(path, *, rewrite=False, connect=False) -> Optional[sqlite3.Connection]:
    try:
        path = Path(path)
        if rewrite:
            try:
                remove_file_path(path)
            except OSError as e:
                raise FileExistsError(f"Cannot remove (rewrite) file {path}, {e}") from e
        path = make_not_existing_path(path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        connection = sqlite3.connect(path)
        if connect:
            _connection_setup(connection)
            return connection
        connection.close()
    except (FileExistsError, sqlite3.Error) as e:
        raise StorageError(original_exception=e) from e
    return None


def db_connect(path) -> sqlite3.Connection:
    try:
        path = make_existing_file_path(path)
        connection = sqlite3.connect(path, isolation_level="EXCLUSIVE", cached_statements=128, check_same_thread=True)
    except (FileNotFoundError, sqlite3.Error) as e:
        raise StorageError(original_exception=e) from e
    try:
        with closing(connection.cursor()) as cursor:
            cursor.execute("PRAGMA schema_version")
    except sqlite3.Error as e:
        connection.close()
        raise StorageError(f"Database connection test failed {path}", original_exception=e) from e
    _connection_setup(connection)
    return connection


def _connection_setup(connection):
    connection.row_factory = sqlite3.Row
    with closing(connection.cursor()) as cursor:
        cursor.execute("PRAGMA foreign_keys = ON")


def get_changed_rows_count(connection):
    return connection.total_changes


def execute_sql(connection, sql_text, *, close_cursor=False, fetch_one=False) -> Union[sqlite3.Cursor, sqlite3.Row, None]:
    cursor = connection.cursor()
    with utils.common.CloseOnError(cursor):
        cursor.execute(sql_text)
    if fetch_one:
        row = cursor.fetchone()
        cursor.close()
        return row
    if close_cursor:
        cursor.close()
        return None
    return cursor


def create_table_raw(connection, table_name, *columns: pypika.Column, primary_key: str = None, foreign_key: ForeignKey = None, unique=tuple()):
    query = pypika.Query.create_table(table_name).columns(*columns)
    if primary_key:
        query = query.primary_key(primary_key)
    if foreign_key:
        query = query.foreign_key([foreign_key.column], pypika.Table(foreign_key.ref_table), [foreign_key.ref_column])
    for col_name in unique:
        query = query.unique(col_name)
    execute_sql(connection, query.get_sql(), close_cursor=True)


def delete_table_raw(connection, table_name):
    query = pypika.Query.drop_table(table_name)
    execute_sql(connection, query.get_sql(), close_cursor=True)


def create_index_raw(connection, table_name, col_name):
    execute_sql(connection, f"CREATE INDEX index_{table_name}_{col_name} ON {table_name}({col_name})", close_cursor=True)


def get_record_raw(connection, table, column, value):
    table = pypika.Table(table)
    query = pypika.Query.from_(table).where(getattr(table, column) == value).select("*")
    return execute_sql(connection, query.get_sql(), fetch_one=True)


def insert_record_raw(connection, table, *values, columns=None, rowid=False) -> Optional[int]:
    table = pypika.Table(table)
    query = pypika.Query.into(table)
    if columns:
        query = query.columns(*columns)
    query = query.insert(*values)
    with closing(execute_sql(connection, query.get_sql())) as cursor:
        if rowid:
            return cursor.lastrowid
    return None


def update_record_raw(connection, table, col_name, col_value, values: dict):
    table = pypika.Table(table)
    query = pypika.Query.update(table)
    for name, value in values.items():
        query = query.set(getattr(table, name), value)
    query = query.where(getattr(table, col_name) == col_value)
    execute_sql(connection, query.get_sql(), close_cursor=True)


def delete_record_raw(connection, table, col_name, col_value):
    table = pypika.Table(table)
    query = pypika.Query.from_(table).where(getattr(table, col_name) == col_value).delete()
    execute_sql(connection, query.get_sql(), close_cursor=True)


def iterate_table_raw(connection, table, callback=None):
    query = pypika.Query.from_(table).select(STAR)
    yield from iterate_query_raw(connection, query.get_sql(), callback=callback)


def iterate_query_raw(connection, sql_text, *, callback=None, fetch_count=8):
    with closing(execute_sql(connection, sql_text)) as cursor:
        cursor.arraysize = fetch_count
        while True:
            rows = cursor.fetchmany()
            if not rows:
                break
            if callback:
                yield from (callback(row) for row in rows)
            else:
                yield from rows


def count_star_raw(connection, table):
    row = execute_sql(connection, f"SELECT COUNT(*) as count_result FROM {table}", fetch_one=True)
    return row["count_result"]


def get_db_tables_raw(connection) -> List[str]:
    return list(row["name"] for row in iterate_query_raw(connection, "SELECT name FROM sqlite_master WHERE type='table'"))


def is_table_exist_raw(connection, table: str):
    row = execute_sql(connection, f"SELECT COUNT(*) as count_result FROM sqlite_master WHERE type='table' AND name='{table}'", fetch_one=True)
    return row["count_result"] > 0


def get_table_columns_raw(connection, table_name) -> List[str]:
    table_columns_gen = iterate_query_raw(connection, f"PRAGMA table_info({table_name})")
    return [row["name"] for row in table_columns_gen]
