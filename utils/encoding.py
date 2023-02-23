import base64
import json
import lzma


UTF8 = "utf-8"
ASCII = "ascii"


def encode_utf8(data: str) -> bytes:
    data = data.encode(UTF8)
    return data


def decode_utf8(data: bytes) -> str:
    data = data.decode(UTF8)
    return data


def encode_ascii(data: str) -> bytes:
    data = data.encode(ASCII)
    return data


def decode_ascii(data: bytes) -> str:
    data = data.decode(ASCII)
    return data


def encode_base64(data: bytes) -> str:
    data = base64.standard_b64encode(data)
    data = decode_ascii(data)
    return data


def decode_base64(data: str) -> bytes:
    data = base64.standard_b64decode(data)
    return data


def encode_json(data: dict) -> str:
    data = json.dumps(data, ensure_ascii=True, allow_nan=True, separators=(",", ":"))
    return data


def decode_json(data: str) -> dict:
    data = json.loads(data)
    return data


def encode_json_base64(data: dict) -> str:
    data = encode_json(data)
    data = encode_utf8(data)
    data = encode_base64(data)
    return data


def decode_json_base64(data: str) -> dict:
    data = decode_base64(data)
    data = decode_utf8(data)
    data = decode_json(data)
    return data


_LZMA_FILTERS = \
[
    {
        "id": lzma.FILTER_LZMA2,
        "preset": 9 | lzma.PRESET_EXTREME
    }
]


def compress_bytes(data: bytes) -> bytes:
    data = lzma.compress(data, lzma.FORMAT_RAW, lzma.CHECK_NONE, None, _LZMA_FILTERS)
    return data


def decompress_bytes(data: bytes) -> bytes:
    data = lzma.decompress(data, lzma.FORMAT_RAW, None, _LZMA_FILTERS)
    return data
