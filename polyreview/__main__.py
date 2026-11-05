import argparse
import sys

from .review import review_path, to_json, to_markdown


def main() -> None:
    ap = argparse.ArgumentParser(prog="polyreview", description="Static code review for Python, JS/TS, Java and Go")
    ap.add_argument("path"); ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--fail-under", type=int, help="exit 1 if any file scores below this (CI gate)")
    a = ap.parse_args()
    reports = review_path(a.path)
    print(to_json(reports) if a.format == "json" else to_markdown(reports))
    if a.fail_under is not None and any(r.score < a.fail_under for r in reports):
        sys.exit(1)


main()
