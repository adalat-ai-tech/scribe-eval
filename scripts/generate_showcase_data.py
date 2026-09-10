"""Bake showcase results for the demo page.

Runs every entry in site/data/showcases.json through demo_api (the same
code path the live in-browser demo uses) and writes the results keyed by
showcase id. The page renders these instantly on load, before — or
without — Pyodide.

Usage:
    python scripts/generate_showcase_data.py \
        --showcases site/data/showcases.json \
        --out site/data/showcase_results.json
"""

import argparse
import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def load_demo_api():
    path = REPO_ROOT / "site" / "py" / "demo_api.py"
    spec = importlib.util.spec_from_file_location("demo_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--showcases", default=REPO_ROOT / "site/data/showcases.json")
    parser.add_argument("--out", default=REPO_ROOT / "site/data/showcase_results.json")
    args = parser.parse_args()

    demo_api = load_demo_api()
    showcases = json.loads(Path(args.showcases).read_text(encoding="utf-8"))

    results = {
        case["id"]: demo_api.evaluate_single(
            case["ref"],
            case["hyp"],
            case["domain"],
            case["normalize"],
            case["use_sandhi"],
        )
        for case in showcases
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Baked {len(results)} showcase results -> {out}")


if __name__ == "__main__":
    main()
