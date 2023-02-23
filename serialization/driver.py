from .base import serialize, deserialize, ID_KEY


# pylint: disable=redefined-builtin
# pylint: disable=attribute-defined-outside-init


# TODO: Split into 2 classes


class ObjectDriver:

    def __init__(self, *, called_outside=True):
        assert not called_outside

    @staticmethod
    def create_empty(id: int) -> "ObjectDriver":
        result = ObjectDriver(called_outside=False)
        result.id = id
        result.data = {ID_KEY: id}
        return result

    @staticmethod
    def attach(data: dict) -> "ObjectDriver":
        result = ObjectDriver(called_outside=False)
        result.id = data[ID_KEY]
        result.data = data
        return result

    def add_key(self, key: str, value):
        assert self.data.get(key, None) is None, "Key already exist"
        self.data[key] = serialize(value)

    def get_key(self, key: str):
        return deserialize(self.data[key])

    def iter_keys(self):
        for k in self.data.keys():
            if k != ID_KEY:
                yield k
