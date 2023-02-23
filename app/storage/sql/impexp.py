import contextlib

from . import content
from . import description
from . import raw


# pylint: disable-next=redefined-builtin
def export_tables(ctx, dump_path, *tables: str, rewrite=False, all=False):
    if all:
        tables = tuple(desc.name for desc in description.iterate_with_decryption(ctx))
    connection_dump = raw.db_create_new(dump_path, rewrite=rewrite, connect=True)
    with contextlib.closing(connection_dump), connection_dump:
        for table in tables:
            content.export_table(ctx, connection_dump, table)


# pylint: disable-next=redefined-builtin
def import_tables(ctx, dump_path, *tables: str, all=False):
    connection_dump = raw.db_connect(dump_path)
    if all:
        dump_tables = raw.get_db_tables_raw(connection_dump)
        prefix, prefix_size = content.DUMP_TABLE_PREFIX, len(content.DUMP_TABLE_PREFIX)
        tables = tuple(table[prefix_size:] for table in dump_tables if table.startswith(prefix))
    with contextlib.closing(connection_dump), ctx.connection:
        for table in tables:
            content.import_table(ctx, connection_dump, table)
