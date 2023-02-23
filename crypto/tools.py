import secrets


def bytes_add_padding(data: bytes, prefix_size: int = 0, postfix_size: int = 0):
    assert 0 <= prefix_size < 256 and 0 <= postfix_size < 256
    prefix = bytes(secrets.randbelow(256) for _ in range(prefix_size))
    postfix = bytes(secrets.randbelow(256) for _ in range(postfix_size))
    return b"".join([bytes([prefix_size]), prefix, data, postfix, bytes([postfix_size])])


def bytes_del_padding(data: bytes):
    prefix_size, postfix_size = data[0], data[-1]
    begin, end = prefix_size + 1, -postfix_size - 1
    return data[begin:end]


def encode_add_padding(data: bytes, min_output_size = 0, max_rnd_size = 0):
    assert min_output_size >= 0 and max_rnd_size >= 0
    prefix_size, postfix_size = 0, 0
    if len(data) < min_output_size:
        prefix_size += secrets.randbelow(min_output_size - len(data) + 1)
        postfix_size += min_output_size - len(data) - prefix_size
    prefix_size += secrets.randbelow(max_rnd_size + 1)
    postfix_size += secrets.randbelow(max_rnd_size + 1)
    return bytes_add_padding(data, prefix_size, postfix_size)


def decode_add_padding(data: bytes):
    return bytes_del_padding(data)
