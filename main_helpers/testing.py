import unittest

from pathlib import Path
from typing import Union, List


def fill_test_suite(src: Union[unittest.TestCase, unittest.TestSuite], dst: unittest.TestSuite, pattern: List[str]):
    if isinstance(src, unittest.TestSuite):
        for item in src:
            fill_test_suite(item, dst, pattern)
    else:
        assert isinstance(src, unittest.TestCase), "Invalid test item type"
        if any(p in src.id() for p in pattern):
            print(src.id())
            dst.addTest(src)


def run(args) -> int:
    test_loader = unittest.TestLoader()
    project_dir = Path(__file__).parent.parent
    test_package = project_dir.joinpath("test")
    full_test_suite = test_loader.discover(str(test_package), pattern="*.py", top_level_dir=str(project_dir))
    test_suite = unittest.TestSuite()
    fill_test_suite(full_test_suite, test_suite, args.test)
    test_result = unittest.TestResult()
    test_suite.run(test_result,)
    errors = [*test_result.errors, *test_result.failures]
    for instance, traceback in errors:
        print(" " * 4, instance.id(), "\n", sep="")
        splitted = traceback.split("\n")
        for s in splitted:
            print(" " * 12, s, sep="")
    print("Tests:", test_suite.countTestCases())
    print("Errors:", len(errors), "\n")
    return len(errors)
