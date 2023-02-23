from unittest import TestCase
from pathlib import Path

from app.storage.sql.share import StorageError
from app.ui.console.app import AppState
from app.config import curconfig


DB_PATH = Path("__test.db")
DUMP_PATH = Path(curconfig.db_directory, "__test_dump.dump")
IMP_DB_PATH = Path("__test_from_dump.db")


class AppCmdTests(TestCase):

    def setUp(self):
        self.app_state = AppState()
        self.app_state.cmd_newdb_backend(DB_PATH, password="hello", rewrite=True, connect=True)

    def tearDown(self):
        self.app_state.cmd_discon_backend()

    def test_0(self):
        self.app_state.cmd_newtable_backend("passwords")
        self.app_state.cmd_ins_backend("passwords", "site.com", "login:login", "password:password")
        res = self.app_state.cmd_get_backend("passwords", "site.com")
        self.assertEqual(res["login"], "login")
        self.assertEqual(res["password"], "password")

    def test_1(self):
        self.app_state.cmd_newtable_backend("passwords")
        self.app_state.cmd_newtable_backend("sometable")
        tables = [desc.name for desc in self.app_state.cmd_tables_backend()]
        self.assertEqual(len(tables), 2)
        self.assertIn("passwords", tables)
        self.assertIn("sometable", tables)

    def test_2(self):
        self.app_state.cmd_newtable_backend("passwords")
        self.app_state.cmd_ins_backend("passwords", "yandex", "password:test")
        data = self.app_state.cmd_get_backend("passwords", "yandex")
        self.assertEqual(data["password"], "test")
        self.app_state.cmd_upd_backend("passwords", "yandex", "password:test_updated")
        data = self.app_state.cmd_get_backend("passwords", "yandex")
        self.assertEqual(data["password"], "test_updated")

    def test_3(self):
        self.app_state.cmd_newtable_backend("passwords")
        self.app_state.cmd_ins_backend("passwords", "yandex", "password:test", "login:test")
        self.app_state.cmd_upd_backend("passwords", "yandex", "password:test_updated", replace=True)
        data = self.app_state.cmd_get_backend("passwords", "yandex")
        self.assertEqual(data["password"], "test_updated")
        self.assertNotIn("login", data)

    def test_4(self):
        self.app_state.cmd_setdbid_backend("FFFFFF")
        dbid = self.app_state.cmd_dbid_backend()
        self.assertEqual("FFFFFF", dbid)

    def test_5(self):
        conpath = self.app_state.cmd_coninfo_backend()
        self.assertIn("__test.db", str(conpath))

    def test_6(self):
        self.app_state.cmd_discon_backend()
        self.assertRaises(AssertionError, self.app_state.cmd_tables_backend)

    def test_7(self):
        self.app_state.cmd_newtable_backend("t1")
        self.app_state.cmd_export_backend(DUMP_PATH, "t1", rewrite=True)
        self.app_state.cmd_newdb_backend(IMP_DB_PATH, password="hello666", rewrite=True, connect=True)
        self.assertRaises(StorageError, self.app_state.cmd_import_backend, DUMP_PATH, "t1")

    def test_8(self):
        self.app_state.cmd_newtable_backend("t1")
        self.app_state.cmd_export_backend(DUMP_PATH, "t1", rewrite=True)
        self.app_state.cmd_newdb_backend(IMP_DB_PATH, password="hello666", rewrite=True, connect=True)
        self.app_state.cmd_newtable_backend("t1")
        self.app_state.cmd_ins_backend("t1", "k", "v:123")
        self.assertRaises(StorageError, self.app_state.cmd_import_backend, DUMP_PATH, "t1")

    def test_9(self):
        self.app_state.cmd_newtable_backend("t1")
        self.app_state.cmd_newtable_backend("t2")
        for i in range(3):
            self.app_state.cmd_ins_backend("t1", str(i), f"{i}:{i}")
        for i in range(3):
            self.app_state.cmd_ins_backend("t2", str(i), f"{i*2}:{i*2}")
        self.app_state.cmd_export_backend(DUMP_PATH, rewrite=True, all=True)
        self.app_state.cmd_newdb_backend(IMP_DB_PATH, password="hello4", rewrite=True, connect=True)
        self.app_state.cmd_newtable_backend("t1", hash_search=True)
        self.app_state.cmd_newtable_backend("t2")
        self.app_state.cmd_import_backend(DUMP_PATH, all=True)
        self.assertEqual(3, self.app_state.cmd_count_backend("t1"))
        self.assertEqual(3, self.app_state.cmd_count_backend("t2"))
        for i in range(3):
            row = self.app_state.cmd_get_backend("t1", str(i))
            self.assertEqual(str(i), row[str(i)])
        for i in range(3):
            row = self.app_state.cmd_get_backend("t2", str(i))
            self.assertEqual(str(i * 2), row[str(i * 2)])

    def test_10(self):
        self.app_state.cmd_newtable_backend("passwords", hash_search=True)
        self.app_state.cmd_ins_backend("passwords", "yandex", "password:test", "login:test")
        self.app_state.cmd_upd_backend("passwords", "yandex", new_key="yandex_new_key")
        data = self.app_state.cmd_get_backend("passwords", "yandex_new_key")
        self.assertEqual(data["password"], "test")
        self.assertEqual(data["login"], "test")
        self.assertEqual(len(data), 2)
        data = self.app_state.cmd_get_backend("passwords", "yandex")
        self.assertEqual(data, None)

    def test_100(self):
        tname = "passwords"
        self.app_state.cmd_newtable_backend(tname, hash_search=True)
        self.app_state.cmd_ins_backend(tname, "yandex", "login:test")
        self.app_state.cmd_ins_backend(tname, "google", "password:123", "login:test")
        self.app_state.cmd_ins_backend(tname, "github", "login:test2")
        klist = self.app_state.cmd_find_backend(tname, "goo")
        self.assertIn("google", klist)
        klist = self.app_state.cmd_keys_backend(tname)
        self.assertEqual(len(klist), 3)
        val = self.app_state.cmd_get_backend(tname, "github")
        self.assertEqual(val["login"], "test2")
        desc = self.app_state.cmd_desctable_backend(tname)
        self.assertEqual(desc.name, "passwords")
        self.assertEqual(desc.hash_search_enabled, True)
        tlist = self.app_state.cmd_tables_backend()
        self.assertEqual(len(tlist), 1)
        self.app_state.cmd_export_backend(DUMP_PATH, rewrite=True, all=True)
        self.app_state.cmd_del_backend(tname, "google")
        klist = self.app_state.cmd_keys_backend(tname)
        self.assertEqual(len(klist), 2)
        self.app_state.cmd_del_backend(tname, "google")
        self.app_state.cmd_del_backend(tname, "yandex")
        self.app_state.cmd_del_backend(tname, "github")
        klist = self.app_state.cmd_keys_backend(tname)
        self.assertEqual(len(klist), 0)
        self.app_state.cmd_deltable_backend(tname)
        tlist = self.app_state.cmd_tables_backend()
        self.assertEqual(len(tlist), 0)
        self.app_state.cmd_newdb_backend(IMP_DB_PATH, password="hello2", connect=True, rewrite=True)
        self.app_state.cmd_newtable_backend(tname, hash_search=False)
        self.app_state.cmd_import(DUMP_PATH, all=True)
        klist = self.app_state.cmd_keys_backend(tname)
        self.assertEqual(len(klist), 3)
        val = self.app_state.cmd_get_backend(tname, "github")
        self.assertEqual(val["login"], "test2")
        val = self.app_state.cmd_get_backend(tname, "xxx")
        self.assertIsNone(val)


