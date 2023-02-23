from unittest import TestCase

from dataclasses import dataclass
from pathlib import Path

from app.config import ConfigEntry, ConfigError


@dataclass(init=False)
class TestEntry2(ConfigEntry):
    s: str = None
    p: Path = None


@dataclass(init=False)
class TestEntry1(ConfigEntry):
    s: str = None
    p: Path = None
    e2: TestEntry2 = None


class ConfigEntryTests(TestCase):

    def test_0(self):
        e1 = TestEntry1()
        e1.set_entry("xxx", "s")
        self.assertEqual(e1.s, "xxx")

    def test_1(self):
        e1 = TestEntry1()
        e1.set_entry("xxx", "p")
        self.assertEqual(e1.p, Path("xxx"))

    def test_2(self):
        e1 = TestEntry1()
        self.assertRaises(ConfigError, e1.set_entry, "xxx", "unknown_key")

    def test_3(self):
        e1 = TestEntry1()
        e1.set_entry("xxx", "e2.s")
        self.assertEqual(e1.e2.s, "xxx")

    def test_4(self):
        e1 = TestEntry1()
        e1.set_entry("xxx", "e2.p")
        self.assertEqual(e1.e2.p, Path("xxx"))

    def test_5(self):
        e1 = TestEntry1()
        self.assertRaises(ConfigError, e1.set_entry, "xxx", "e2.unknown_key")

    def test_6(self):
        e1 = TestEntry1()
        self.assertRaises(ConfigError, e1.set_entry, "xxx", ".fdfd..")

    def test_7(self):
        e1 = TestEntry1()
        self.assertRaises(ConfigError, e1.set_entry, 1, "s")

    def test_8(self):
        e1 = TestEntry1()
        self.assertRaises(ConfigError, e1.set_entry, 1, "e2.s")
