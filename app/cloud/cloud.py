import datetime

from contextlib import closing

from app import config

from app.storage import sql
# pylint: disable-next=unused-import
import app.storage.sql.manifest
# pylint: disable-next=unused-import
import app.storage.sql.raw

from . import dropbox
from . import yandex_disk

from .share import CloudError


def _check_service(service):
    default_service = config.curconfig.cloud.service
    config.curconfig.cloud.service = service
    error = None
    try:
        config.curconfig.cloud.check()
    except config.ConfigError as e:
        error = e
    finally:
        config.curconfig.cloud.service = default_service
    if error:
        raise CloudError("Cloud service config error", original_exception=error)


def init_cloud(service):
    if service != config.curconfig.cloud.service:
        _check_service(service)
    if service == "dropbox":
        return DropboxCloud()
    if service == "yandex_disk":
        return YandexDiskCloud()
    assert False, "Unreacheable code"


# pylint: disable-next=too-few-public-methods
class DropboxCloud:

    def __init__(self):
        refresh_token_path = config.curconfig.cloud.dropbox.refresh_token_path
        with open(refresh_token_path, "r", encoding="utf-8") as fd:
            refresh_token = fd.read().rstrip(" \r\n")
        self.cloud_directory = config.curconfig.cloud.dropbox.upload_directory
        self.dropbox = dropbox.Dropbox(refresh_token, update_access_token=True)

    def upload_database(self, path):
        cloud_filename = _gen_cloud_filename(path)
        cloud_path = f"{self.cloud_directory}{cloud_filename}"
        self.dropbox.upload_file(cloud_path, path)


# pylint: disable-next=too-few-public-methods
class YandexDiskCloud:

    def __init__(self):
        access_token_path = config.curconfig.cloud.yandex_disk.access_token_path
        with open(access_token_path, "r", encoding="utf-8") as fd:
            access_token = fd.read().rstrip(" \r\n")
        self.cloud_directory = config.curconfig.cloud.yandex_disk.upload_directory
        self.yandex_disk = yandex_disk.YandexDisk(access_token)

    def upload_database(self, path):
        cloud_filename = _gen_cloud_filename(path)
        cloud_path = f"{self.cloud_directory}{cloud_filename}"
        self.yandex_disk.upload_file(cloud_path, path)


def _gen_cloud_filename(local_path):
    with closing(sql.raw.db_connect(local_path)) as connection:
        if not sql.manifest.is_db_created_by_app(connection):
            raise CloudError("File is not created by application")
        dbid = sql.manifest.get_dbid(connection)
    filename = local_path.name
    current_time_z = datetime.datetime.now(datetime.timezone(datetime.timedelta(0)))
    time_str = current_time_z.strftime("%Y_%m_%d_%H_%M_%S")
    return f"{dbid}_{time_str}_{filename}"
