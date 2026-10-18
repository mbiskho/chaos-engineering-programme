from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .runner import run
from .spec import SpecError, load
from .steady import Prometheus


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chaos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate").add_argument("path", type=Path)
    r = sub.add_parser("run")
    r.add_argument("experiment", type=Path)
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--results", type=Path, default=Path("results"))
    a = ap.parse_args(argv)

    if a.cmd == "validate":
        files = sorted(a.path.glob("*.yaml")) if a.path.is_dir() else [a.path]
        bad = 0
        for f in files:
            try:
                load(f)
                print(f"ok    {f}")
            except SpecError as e:
                bad += 1
                print(f"FAIL  {e}")
        return 1 if bad else 0

    exp = load(a.experiment)
    prom = Prometheus(os.environ.get("PROMETHEUS_URL", "http://localhost:9090"))
    result = run(exp, prom, a.results, a.dry_run)
    print(f"{exp.name}: {result['result']}")
    return 0 if result["result"] in ("hypothesis-held", "dry-run") else 1


if __name__ == "__main__":
    sys.exit(main())
