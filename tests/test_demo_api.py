"""Contract tests for the demo page's Python helper (site/py/demo_api.py).

These run in CPython with the real Levenshtein package; the Pyodide
environment differs only in the shim, whose parity is pinned by
tests/test_levenshtein_shim.py.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

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
    assert set(result) == {"alignment", "tiles", "chips", "contribution", "errors", "plain"}
    assert set(result["plain"]) == {"wer", "cer", "subs", "ins", "dels", "alignment"}
    for row in result["plain"]["alignment"]:
        assert set(row) == {"ref_text", "hyp_text", "error_type"}
    for record in result["errors"]:
        assert {"error_type", "category", "ref_token", "hyp_token"} <= set(record)
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


def test_statute_showcase_is_one_numeral_error():
    result = run_case(BY_ID["legal-statute"])
    numerals = [row["ref_text"] for row in result["alignment"] if row["token_type"] == "NUMERAL"]
    assert numerals == ["32(1)(a)"]
    assert [(e["error_type"], e["category"]) for e in result["errors"]] == [
        ("substitution", "NUMERAL")
    ]
    assert result["plain"]["subs"] + result["plain"]["ins"] + result["plain"]["dels"] == 2


def test_numeral_showcase_normalization_effect():
    case = BY_ID["numeral-norm"]
    normalized = run_case(case)
    assert normalized["tiles"]["wer_scribe"] == 0.0
    raw = run_case(case, normalize=False)
    assert raw["tiles"]["wer_scribe"] > 0.0


def test_json_round_trip():
    case = BY_ID["ml-merge-split"]
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
    assert result["plain"]["ins"] == 2


def test_empty_hypothesis_is_all_deletions():
    plain = demo_api.evaluate_single("two words", "")["plain"]
    assert plain["wer"] == 1.0
    assert plain["dels"] == 2


def test_plain_wer_flags_sandhi_that_scribe_forgives():
    # The contrast the page shows: every word wrong for plain WER, no
    # lexical error for SCRIBE.
    result = run_case(BY_ID["ml-merge-split"])
    assert result["plain"]["wer"] == 1.0
    assert not any(
        row["error_type"] != "correct"
        and row["token_type"] == "LEXICAL"
        and row["error_type"] != "sandhi"
        for row in result["alignment"]
    )


def test_plain_rates_match_jiwer():
    jiwer = pytest.importorskip("jiwer")
    for case in SHOWCASES:
        plain = run_case(case)["plain"]
        assert plain["wer"] == pytest.approx(jiwer.wer(case["ref"], case["hyp"])), case["id"]
        assert plain["cer"] == pytest.approx(jiwer.cer(case["ref"], case["hyp"])), case["id"]
        counts = jiwer.process_words(case["ref"], case["hyp"])
        assert (plain["subs"], plain["ins"], plain["dels"]) == (
            counts.substitutions,
            counts.insertions,
            counts.deletions,
        ), case["id"]


def test_readme_sandhi_rows_are_showcases():
    # The README Sandhi Awareness table and the demo showcases must not drift.
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Sandhi Awareness")[1].split("## Domain Configuration")[0]
    rows = re.findall(r"^\| \w+ \| (.+?) \| (.+?) \|", section, flags=re.MULTILINE)
    rows = [pair for pair in rows if pair != ("Reference", "Hypothesis")]
    assert rows, "README Sandhi Awareness table not found"
    # A README row may be a fragment of a longer showcase utterance, so
    # containment (not equality) is the contract.
    for ref, hyp in rows:
        assert any(
            ref.strip() in case["ref"] and hyp.strip() in case["hyp"] for case in SHOWCASES
        ), (ref, hyp)
