import os

from utils.path import make_existing_file_path

from .share import CloudError, make_request, get_json_field, make_json


CLIENT_ID = "4eb86ca86ee841c3ade52e269bb4dc3d"


# pylint: disable-next=too-few-public-methods
class YandexDisk:

    def __init__(self, access_token):
        self.access_token = access_token
        self.default_headers = {
            "Accept": "application/json",
            "Authorization": f"OAuth {self.access_token}",
        }

    def upload_file(self, cloud_path, local_path):
        local_path = make_existing_file_path(local_path)
        if os.stat(local_path).st_size >= 9 * 10 ** 8:
            raise CloudError("File is too large")
        link = self._get_upload_link(cloud_path)
        with open(local_path, "rb") as f:
            content = f.read()
        headers = {
            **self.default_headers,
            "Content-Type": "application/octet-stream"
        }
        response = make_request("PUT", link, data=content, headers=headers)
        if response.status_code not in (200, 201, 202):
            error = get_json_field(make_json(response.text), "error", default="")
            raise CloudError(f"Cannot upload file, yandex return {response.status_code} {error}")

    def _get_upload_link(self, cloud_path, overwrite=False):
        params = {
            "path": cloud_path,
            "overwrite": "true" if overwrite else "false"
        }
        response = make_request("GET", "https://cloud-api.yandex.net/v1/disk/resources/upload", headers=self.default_headers, params=params)
        js = make_json(response.text)
        if response.status_code != 200:
            error = get_json_field(js, "error", default="")
            raise CloudError(f"Cannot get link for file upload, yandex return {response.status_code} {error}")
        if get_json_field(js, "templated", required=True, ftype=bool):
            raise CloudError("Upload link is templated, not implemented")
        return get_json_field(js, "href", required=True)
