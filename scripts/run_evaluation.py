import json
import os
import sys

# Ensure repo root is importable as package root
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.eval.eval_runner import run_cases


def load_cases():
    base = os.path.join(os.getcwd(), "evaluation")
    visible = os.path.join(base, "visible-cases.json")
    additional = os.path.join(base, "additional-cases.json")
    cases = []
    for p in (visible, additional):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases.extend(data.get("cases", []))
    return cases


def main():
    cases = load_cases()
    report = run_cases(cases)
    out_path = os.path.join("evaluation", "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("Evaluation complete")
    print(f"Total: {report['total']} Passed: {report['passed']}")
    print(f"Results written to {out_path}")


if __name__ == "__main__":
    main()
