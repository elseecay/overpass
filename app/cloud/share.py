import json

import requests

from utils.smrtexcp import SmartException


class CloudError(SmartException):
    pass


def make_request(method, url, *, timeout=None, **kwargs) -> requests.Response:
    if timeout is None:
        timeout = 30
    try:
        response = requests.request(method, url, timeout=timeout, **kwargs)
    except requests.RequestException as e:
        raise CloudError(original_exception=e) from e
    return response


def get_json_field(js: dict, name: False, *, ftype=str, required=False, default=None):
    assert required or default is not None
    value = js.get(name, None)
    if required:
        if value is None:
            raise CloudError(f"Invalid cloud service response, missing field {name}")
        if not isinstance(value, ftype):
            raise CloudError(f"Invalid cloud service response, bad type of field {name}")
        return value
    if value is None or not isinstance(value, ftype):
        return default
    return value


def make_json(response_text):
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        raise CloudError(f"Cloud service send invalid json, {e}") from e
