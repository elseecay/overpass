import functools
import itertools
import copy
import secrets

from typing import Union, List

import utils.common

from .base.base import BaseCipher, BaseHash


# pylint: disable=too-few-public-methods


class Hasher:

    def __init__(self, *elements, iterations=1):
        assert len(elements) > 0
        assert all(isinstance(elem, (BaseHash, Hasher)) for elem in elements)
        self.elements = elements
        self.iterations = iterations
        last = elements[-1]
        self.digest_size = last.get_digest_size() if isinstance(last, BaseHash) else last.digest_size

    def process(self, data: bytes) -> bytes:
        elements = itertools.chain.from_iterable(itertools.repeat(self.elements, self.iterations))
        return functools.reduce(lambda accum, elem: elem.process(accum), elements, data)


class KeyHasher:

    def __init__(self, *elements: Union[BaseHash, Hasher]):
        assert len(elements) > 0
        assert all(isinstance(elem, (BaseHash, Hasher)) for elem in elements)
        self.elements = elements
        self.key_sizes = [elem.get_digest_size() if isinstance(elem, BaseHash) else elem.digest_size for elem in self.elements]

    def process(self, key: bytes) -> List[bytes]:
        keys = []
        for elem in self.elements:
            key = elem.process(key)
            keys.append(key)
        return keys


class Mixer:

    def __init__(self, *elements, keys: Union[tuple, list] = None):
        assert len(elements) > 0
        assert all(isinstance(elem, BaseCipher) for elem in elements)
        self.elem_count = len(elements)
        self.elements = tuple(copy.deepcopy(elem) for elem in elements)
        self.iv_size_total = sum((elem.IV_SIZE for elem in self.elements), 0)
        self.iv_sizes = tuple(elem.IV_SIZE for elem in self.elements)
        self.key_sizes = [elem.KEY_SIZE for elem in self.elements]
        self.is_keys_set = False
        self.opp = None
        if keys is not None:
            self.set_keys(*keys)

    def process(self, data: bytes):
        assert self.is_keys_set
        return functools.reduce(lambda accum, elem: elem.process(accum), self.elements, data)

    def opposite_instance(self, set_attribute=False):
        assert self.is_keys_set
        opp_elements = tuple(elem.opposite_instance() for elem in reversed(self.elements))
        opp_keys = tuple(elem.key for elem in reversed(self.elements))
        opp_mixer = Mixer(*opp_elements, keys=opp_keys)
        if set_attribute:
            self.opp = opp_mixer
        return opp_mixer

    def set_keys(self, *keys: bytes):
        assert len(keys) == self.elem_count
        assert all(isinstance(key, bytes) for key in keys)
        assert all(len(key) == elem.KEY_SIZE for key, elem in zip(keys, self.elements))
        for elem, key in zip(self.elements, keys):
            elem.key = key
        self.is_keys_set = True

    def iv_set(self, iv: Union[list, tuple, bytes], iv_order_reverse=True):
        assert isinstance(iv, (bytes, list, tuple))
        if isinstance(iv, bytes):
            iv = utils.common.split_bytes(iv, *self.iv_sizes, full_coverage=True)
        assert len(iv) == self.elem_count
        if iv_order_reverse:
            iv = tuple(reversed(iv))
        for elem, iv_part, iv_part_size in zip(self.elements, iv, self.iv_sizes):
            assert len(iv_part) == iv_part_size
            elem.iv = iv_part

    def iv_set_random(self) -> bytes:
        iv = tuple(secrets.token_bytes(size) for size in self.iv_sizes)
        self.iv_set(iv, iv_order_reverse=False)
        return b"".join(iv)
