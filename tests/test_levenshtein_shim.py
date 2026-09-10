"""Parity tests: site/py/levenshtein_shim.py vs the real Levenshtein package.

The shim runs inside Pyodide where the C extension is unavailable; these
tests pin its contract against the real package in CPython, where both
are importable. The load-bearing guarantee is that every value scribe
derives from editops — cer_scribe, char_errors (= len(ops)) — is
identical; the S/I/D composition is additionally pinned on
natural-language pairs (see the shim's module docstring for why exact
composition parity on adversarial strings is not attainable).
"""

import importlib.util
import random
from pathlib import Path

import Levenshtein as real

_SHIM_PATH = Path(__file__).parent.parent / "site" / "py" / "levenshtein_shim.py"
_spec = importlib.util.spec_from_file_location("levenshtein_shim", _SHIM_PATH)
shim = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shim)

# Reference/hypothesis pairs mirroring what measure.py feeds editops:
# the README Sandhi Awareness rows, the legal and numeral quick-start
# examples, and sentence pairs in all demo scripts.
NATURAL_PAIRS = [
    ("അന്യായ പട്ടിക", "അന്യായപ്പട്ടിക"),
    ("എനിക്ക് അറിയാം", "എനിക്കറിയാം"),
    ("ಪ್ರಧಾನ ಮಂತ್ರಿಗಳ", "ಪ್ರಧಾನಮಂತ್ರಿಗಳ"),
    ("ಮಿತ್ರರಾಷ್ಟ್ರಗಳು", "ಮಿತ್ರ ರಾಷ್ಟ್ರಗಳು"),
    ("भाई साहब", "भाईसाहब"),
    ("उस में", "उसमें"),
    ("charged u/s 302 IPC on 22.05.2023", "charged u/s 303 IPC on 22.05.2023"),
    ("fine of 1,00,000 imposed on 22.05.2023", "fine of 100000 imposed on 22/05/2023"),
    ("ഇന്ന് അല്ലെങ്കിൽ നാളെ", "ഇന്നല്ലെങ്കിൽ നാളെ"),
    ("കണ്ട് പറഞ്ഞു", "കണ്ടറഞ്ഞു"),
    ("ജസ് സോളി ഹാജരായി", "ജസോളി ഹാജരായി"),
    ("പ്രതി കോടതിയിൽ ഹാജരായി എന്ന് സാക്ഷി പറഞ്ഞു", "പ്രതി കോടതിയില്‍ ഹാജരായി എന്ന സാക്ഷി പറഞ്ഞു"),
    ("സാക്ഷി പി ഡബ്ല്യു ഒന്ന് മൊഴി നൽകി", "സാക്ഷി പി ഡബ്ല്യു ഒന്ന് മൊഴി നല്കി"),
    ("ബോധ്യപ്പെടുത്തി തന്നത് ശരിയാണ്", "ബോധ്യപ്പെടുത്തുന്നത് ശരിയാണ്"),
    ("ಸಾಕ್ಷಿ ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಹಾಜರಾದರು", "ಸಾಕ್ಷಿ ನ್ಯಾಯಾಲಯದಲ್ಲಿ ಹಾಜರಾದರೂ"),
    ("ಅವರು ಇಂದು ಬಂದಿದ್ದಾರೆ", "ಅವರು ಇಂದು ಬಂದಿದ್ದಾರೆ"),
    ("गवाह ने अदालत में बयान दिया", "गवाह ने अदालत मे बयान दिया"),
    ("जा कर देखो वहाँ क्या हुआ", "जाकर देखो वहां क्या हुआ"),
    ("the witness appeared before the court", "the witness appears before the court"),
    ("section three hundred two of the penal code", "section three hundred and two of penal code"),
    ("", ""),
    ("", "hallucinated"),
    ("deleted entirely", ""),
]


def _random_pairs(count, alphabet, max_len, seed):
    rng = random.Random(seed)
    pairs = []
    for _ in range(count):
        a = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, max_len)))
        b = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, max_len)))
        pairs.append((a, b))
    return pairs


FUZZ_PAIRS = _random_pairs(1500, "abcde ", 12, seed=20260910) + _random_pairs(
    1500, "കണ്ടപറഞ്ഞു ಮಿತ್ರ भाई ", 12, seed=20260911
)


def test_distance_parity_natural():
    for a, b in NATURAL_PAIRS:
        assert shim.distance(a, b) == real.distance(a, b), (a, b)


def test_distance_parity_fuzz():
    for a, b in FUZZ_PAIRS:
        assert shim.distance(a, b) == real.distance(a, b), (a, b)


def test_editops_len_equals_distance():
    # Any minimal edit script has exactly `distance` operations — this is
    # what makes cer_scribe/char_errors tie-break-invariant.
    for a, b in NATURAL_PAIRS + FUZZ_PAIRS[:500]:
        dist = real.distance(a, b)
        assert len(shim.editops(a, b)) == dist, (a, b)
        assert len(real.editops(a, b)) == dist, (a, b)


def test_editops_tags_valid():
    for a, b in NATURAL_PAIRS:
        tags = {op[0] for op in shim.editops(a, b)}
        assert tags <= {"replace", "insert", "delete"}, (a, b, tags)


def test_sid_split_parity_natural():
    # Composition parity is pinned on natural language only (see shim
    # docstring); the sum is invariant everywhere.
    for a, b in NATURAL_PAIRS:
        shim_ops = shim.editops(a, b)
        real_ops = real.editops(a, b)
        for tag in ("replace", "insert", "delete"):
            assert sum(1 for op in shim_ops if op[0] == tag) == sum(
                1 for op in real_ops if op[0] == tag
            ), (a, b, tag)


def test_measure_consumption_parity(monkeypatch):
    # compute_cer_scribe must produce the identical dict whether editops
    # comes from the C extension or the shim.
    import scribe.measure
    from scribe import compute_cer_scribe

    expected = [compute_cer_scribe(a, b) for a, b in NATURAL_PAIRS]
    monkeypatch.setattr(scribe.measure, "editops", shim.editops)
    actual = [compute_cer_scribe(a, b) for a, b in NATURAL_PAIRS]
    assert actual == expected


def test_empty_and_identical_strings():
    assert shim.distance("", "") == 0
    assert shim.editops("", "") == []
    assert shim.distance("abc", "abc") == 0
    assert shim.editops("abc", "abc") == []
    assert shim.distance("", "ab") == 2
    assert [op[0] for op in shim.editops("", "ab")] == ["insert", "insert"]
    assert shim.distance("ab", "") == 2
    assert [op[0] for op in shim.editops("ab", "")] == ["delete", "delete"]
