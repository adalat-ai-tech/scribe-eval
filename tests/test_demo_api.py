"""Contract tests for the demo page's Python helper (site/py/demo_api.py).

These run in CPython with the real Levenshtein package; the Pyodide
environment differs only in the shim, whose parity is pinned by
tests/test_levenshtein_shim.py.
"""

import importlib.util
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "demo_api", REPO_ROOT / "site" / "py" / "demo_api.py"
)
demo_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(demo_api)

SHOWCASES = json.loads((REPO_ROOT / "site" / "data" / "showcases.json").read_text(encoding="utf-8"))
BY_ID = {case["id"]: case for case in SHOWCASES}


def run_case(case, **overrides):
    params = {
        "ref": case["ref"],
        "hyp": case["hyp"],
        "domain_name": case["domain"],
        "normalize": case["normalize"],
        "use_sandhi": case["use_sandhi"],
    }
    params.update(overrides)
    return demo_api.evaluate_single(**params)


def test_result_schema():
    result = run_case(BY_ID["legal"])
    assert set(result) == {"alignment", "tiles", "chips", "contribution"}
    assert set(result["tiles"]) == {"wer_scribe", "cer_scribe", "accuracy", "sandhi_hits"}
    for row in result["alignment"]:
        assert {"ref_text", "hyp_text", "error_type", "token_type"} <= set(row)
    assert isinstance(result["chips"], list)
    assert isinstance(result["contribution"], list)


def test_every_showcase_evaluates():
    for case in SHOWCASES:
        result = run_case(case)
        assert result["alignment"], case["id"]


def test_sandhi_showcase_scores_zero_with_detection():
    case = BY_ID["ml-elision"]
    with_sandhi = run_case(case)
    assert with_sandhi["tiles"]["wer_scribe"] == 0.0
    assert with_sandhi["tiles"]["sandhi_hits"] >= 1
    assert any(row["error_type"] == "sandhi" for row in with_sandhi["alignment"])

    without = run_case(case, use_sandhi=False)
    assert without["tiles"]["wer_scribe"] > 0.0
    assert without["tiles"]["sandhi_hits"] == 0


def test_legal_showcase_tags_domain_tokens():
    result = run_case(BY_ID["legal"])
    assert any(row["token_type"] == "LEGAL" for row in result["alignment"])
    assert any(chip.startswith("Legal Tokens") for chip in result["chips"])


def test_numeral_showcase_normalization_effect():
    case = BY_ID["numeral-norm"]
    normalized = run_case(case)
    assert normalized["tiles"]["wer_scribe"] == 0.0
    raw = run_case(case, normalize=False)
    assert raw["tiles"]["wer_scribe"] > 0.0


def test_json_round_trip():
    case = BY_ID["ml-gemination"]
    payload = demo_api.evaluate_single_json(
        case["ref"], case["hyp"], case["domain"], case["normalize"], case["use_sandhi"]
    )
    assert json.loads(payload) == run_case(case)
    # Indic text must survive un-escaped for the page's renderers.
    assert case["ref"].split()[0] in payload


def test_insertion_only_does_not_crash():
    result = demo_api.evaluate_single("", "hallucinated text")
    assert result["tiles"]["accuracy"] == 0.0
    assert result["tiles"]["wer_scribe"] > 0.0


def test_readme_sandhi_rows_are_showcases():
    # The README Sandhi Awareness table and the demo showcases must not drift.
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Sandhi Awareness")[1].split("## Domain Configuration")[0]
    rows = re.findall(r"^\| \w+ \| (.+?) \| (.+?) \|", section, flags=re.MULTILINE)
    rows = [pair for pair in rows if pair != ("Reference", "Hypothesis")]
    showcase_pairs = {(case["ref"], case["hyp"]) for case in SHOWCASES}
    assert rows, "README Sandhi Awareness table not found"
    for ref, hyp in rows:
        assert (ref.strip(), hyp.strip()) in showcase_pairs, (ref, hyp)
