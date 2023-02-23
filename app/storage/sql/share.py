from dataclasses import dataclass
from sqlite3 import Connection

from utils.smrtexcp import SmartException

from crypto.mixer import Mixer, Hasher


class StorageError(SmartException):
    pass


@dataclass(frozen=True)
class ConnectionContext:
    connection: Connection
    mixer: Mixer
    hs_hasher: Hasher
