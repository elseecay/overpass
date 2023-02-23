import json
import os
import hashlib

from utils.path import make_existing_file_path

from .share import CloudError, make_request, make_json, get_json_field


CLIENT_ID = "70lb3xbyjwf04ly"


class Dropbox:

    def __init__(self, refresh_token, *, update_access_token=False):
        self.refresh_token = refresh_token
        self.access_token = None
        if update_access_token:
            self.update_access_token()

    def update_access_token(self):
        params = {
            "refresh_token": self.refresh_token,
            "client_id": CLIENT_ID,
            "grant_type": "refresh_token"
        }
        response = make_request("POST", "https://api.dropboxapi.com/oauth2/token", params=params)
        if response.status_code != 200:
            raise CloudError(f"Cannot update access token, dropbox return {response.status_code}", "Try to update your refresh token")
        self.access_token = get_json_field(make_json(response.text), "access_token", required=True)

    def upload_file(self, cloud_path, local_path):
        if self.access_token is None:
            raise CloudError("Access token not set")
        local_path = make_existing_file_path(local_path)
        if os.stat(local_path).st_size >= 150 * 10 ** 6:
            raise CloudError("File is too large for upload (150 MB limit)")
        with open(local_path, "rb") as f:
            content = f.read()
        params = {
            "path": cloud_path,
            "mode": "add",
            "autorename": False,
            "strict_conflict": True,
            "content_hash": Dropbox.calculate_dropbox_hash(content),
            "mute": True
        }
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Dropbox-API-Arg": json.dumps(params),
            "Content-Type": "application/octet-stream"
        }
        response = make_request("POST", "https://content.dropboxapi.com/2/files/upload", data=content, headers=headers)
        if response.status_code != 200:
            error = get_json_field(make_json(response.text), "error_summary", default="")
            raise CloudError(f"Cannot upload file, dropbox return {response.status_code} {error}")

    @staticmethod
    def calculate_dropbox_hash(file_content: bytes) -> str:
        """
        Split content for 4 MiB blocks
        Calc SHA256 of each block and concatenate all hashes
        Calc SHA256 of concatenated hashes
        Encode it to hexadecimal
        """
        # pylint: disable-next=invalid-name
        BLOCK_SIZE = 4 * 1024 * 1024
        blocks_count = len(file_content) // BLOCK_SIZE + (1 if len(file_content) % BLOCK_SIZE else 0)
        blocks_hash = []
        for i in range(blocks_count):
            begin = i * BLOCK_SIZE
            end = min((i + 1) * BLOCK_SIZE, len(file_content))
            blocks_hash.append(hashlib.sha256(file_content[begin:end]).digest())
        concatenated = b"".join(blocks_hash)
        return hashlib.sha256(concatenated).digest().hex()
