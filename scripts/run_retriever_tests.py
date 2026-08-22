import runpy
import sys
import os


def run_tests(path: str):
    repo_root = os.getcwd()
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    mod_globals = runpy.run_path(path)
    tests = [v for k, v in mod_globals.items() if callable(v) and k.startswith("test_")]
    passed = 0
    failed = 0
    failures = []
    for t in tests:
        try:
            print(f"RUNNING {t.__name__}...", end=" ")
            t()
            print("OK")
            passed += 1
        except AssertionError as e:
            print("FAIL")
            failed += 1
            failures.append((t.__name__, str(e)))
        except Exception as e:
            print("ERROR")
            failed += 1
            failures.append((t.__name__, repr(e)))

    print("\nRESULTS")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    if failures:
        print("\nFailures:")
        for name, err in failures:
            print(f" - {name}: {err}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    module_path = "tests/test_retriever.py"
    sys.exit(run_tests(module_path))
