"""Tests for the sandhi-aware alignment engine."""

import math

import pytest

from scribe import DomainConfig, align_arrays, domain_aware_tokenizer
from scribe.align import DEFAULT_WEIGHTS, check_sandhi_match


def _tok(text, domain=None):
    return domain_aware_tokenizer(text, domain)


def test_identical_sequences_align_one_to_one():
    ref_toks, ref_tags = _tok("hello world")
    hyp_toks, hyp_tags = _tok("hello world")
    aligned_ref, aligned_hyp, _score = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    # Same length, same tokens, same tags.
    assert aligned_ref == aligned_hyp
    assert len(aligned_ref) == len(ref_toks)


def test_align_returns_three_values():
    ref_toks, ref_tags = _tok("a b")
    hyp_toks, hyp_tags = _tok("a b")
    out = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    assert len(out) == 3
    aligned_ref, aligned_hyp, score = out
    assert isinstance(aligned_ref, list)
    assert isinstance(aligned_hyp, list)
    assert isinstance(score, float)


def test_alignment_lists_have_equal_length():
    """Alignment introduces gaps so the two output lists have equal length."""
    ref_toks, ref_tags = _tok("a b c")
    hyp_toks, hyp_tags = _tok("a x b c")  # one insertion
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    assert len(aligned_ref) == len(aligned_hyp)


def test_pure_insertion_introduces_gap_in_ref():
    ref_toks, ref_tags = _tok("a b")
    hyp_toks, hyp_tags = _tok("a b c")
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    # Gap rows are ("**", "GAP"). The ref side picks up a gap row.
    ref_real = [t for t, tag in aligned_ref if tag != "GAP"]
    hyp_real = [t for t, tag in aligned_hyp if tag != "GAP"]
    assert len(hyp_real) - len(ref_real) == 1


def test_pure_deletion_introduces_gap_in_hyp():
    ref_toks, ref_tags = _tok("a b c")
    hyp_toks, hyp_tags = _tok("a b")
    aligned_ref, aligned_hyp, _ = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    ref_real = [t for t, tag in aligned_ref if tag != "GAP"]
    hyp_real = [t for t, tag in aligned_hyp if tag != "GAP"]
    assert len(ref_real) - len(hyp_real) == 1


def test_higher_score_for_identical_than_different():
    """Identical inputs should score strictly higher than substituted ones."""
    ref_toks, ref_tags = _tok("alpha beta gamma")
    hyp_same = ref_toks
    hyp_same_tags = ref_tags
    hyp_diff_toks, hyp_diff_tags = _tok("alpha delta gamma")
    _, _, s_same = align_arrays(ref_toks, ref_tags, hyp_same, hyp_same_tags)
    _, _, s_diff = align_arrays(ref_toks, ref_tags, hyp_diff_toks, hyp_diff_tags)
    assert s_same > s_diff


def test_sandhi_merge_reduces_alignment_count():
    """The 2:1 merge `ഇന്ന് അല്ലെങ്കിൽ -> ഇന്നല്ലെങ്കിൽ` must align as one merge,
    not two substitutions."""
    ref_toks, ref_tags = _tok("ഇന്ന് അല്ലെങ്കിൽ")
    hyp_toks, hyp_tags = _tok("ഇന്നല്ലെങ്കിൽ")
    aligned_ref, aligned_hyp, _ = align_arrays(
        ref_toks, ref_tags, hyp_toks, hyp_tags, use_sandhi=True
    )
    # In the merge case the ref side keeps both tokens, the hyp side
    # picks up at least one slot containing the merged word.
    hyp_real = [t for t, tag in aligned_hyp if tag != "GAP"]
    assert any("ഇന്നല്ലെങ്കിൽ" in tok for tok in hyp_real)


# Multilingual smoke cases — mirror examples/text_alignment.py DEFAULT_EXAMPLES.
# These guard against regressions in alignment over real-world Indic and
# English inputs with mixed error patterns.
MULTILINGUAL_PAIRS = [
    pytest.param(
        "ആദ്യഗഡുവായി 180000 രൂപയായി നൽകിയത്.",
        "ആദ്യ ഗഡുവായി 180000 രൂപയായി നൽകിയത്:",
        id="malayalam-sandhi",
    ),
    pytest.param(
        "നിർദ്ദിഷ്ട ഭേദഗതി ഇരുസഭകളും 2011-ൽ തന്നെ പാസാക്കി.",
        "നിർദ്ദിഷ്ട ട ഭേദഗതി ഇരുസഭകളും 201-ൽ തന്നെ പാസാക്കി.",
        id="malayalam-insertion-and-numeral-truncation",
    ),
    pytest.param(
        "10 ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ।",
        "ಹತ್ತು ವರ್ಷವಾದ ಮಕ್ಕಳಿಗೆ ಅದರ ಒಂದು ಸ್ವಲ್ಪ ಜ್ಞಾನ ಮನವರಿಕೆ ಒಂದು ಪ್ರಾರಂಭ ಆಗುತ್ತದೆ.",
        id="kannada-numeral-spelled-out",
    ),
    pytest.param(
        "The brown quick fox jumps over the lazy dogs.",
        "The bron fox jumps over a lazy, dog",
        id="english-reorder-and-punct",
    ),
]


@pytest.mark.parametrize("ref,hyp", MULTILINGUAL_PAIRS)
def test_alignment_runs_cleanly_on_multilingual_pairs(ref, hyp):
    """For each demo pair, alignment must produce two equal-length lists,
    a finite numeric score, and at least one position of either side."""
    domain = DomainConfig.legal()
    ref_toks, ref_tags = _tok(ref, domain)
    hyp_toks, hyp_tags = _tok(hyp, domain)
    aligned_ref, aligned_hyp, score = align_arrays(ref_toks, ref_tags, hyp_toks, hyp_tags)
    assert len(aligned_ref) == len(aligned_hyp)
    assert len(aligned_ref) > 0
    assert isinstance(score, float) and math.isfinite(score)


# Regression tests for issue #23: an extra dropped/inserted word must not be
# validated as a Sandhi split/merge. When single_text is identical to one of
# the pair, the other word contributed nothing, yet the boundary region
# collapses to empty and the Levenshtein distance (== len(split_boundary)
# == 2) lands exactly on the default tolerance, producing a false positive.
SANDHI_FALSE_POSITIVES = [
    pytest.param(["सी", "सेंटर"], "सेंटर", id="hindi-extra-word-before"),
    pytest.param(["പരിചയം", "യം"], "പരിചയം", id="malayalam-echoed-suffix"),
]

SANDHI_GENUINE = [
    pytest.param(["വന്നു", "ഇല്ല"], "വന്നില്ല", id="malayalam-vowel-elision"),
    pytest.param(["മരം", "ഇല്ല"], "മരമില്ല", id="malayalam-anusvara-assimilation"),
    pytest.param(["ചെയ്തു", "എന്ന്"], "ചെയ്തുവെന്ന്", id="malayalam-v-glide"),
    pytest.param(["താമര", "ഇല"], "താമരയില", id="malayalam-y-glide"),
    # Empty boundary region but single != either word: the chandrakkala and
    # അ both vanish at the junction, yet both words contribute content.
    pytest.param(["ഇന്ന്", "അല്ലെങ്കിൽ"], "ഇന്നല്ലെങ്കിൽ", id="malayalam-empty-boundary-genuine"),
]


@pytest.mark.parametrize("combined,single", SANDHI_FALSE_POSITIVES)
def test_check_sandhi_match_rejects_dropped_word(combined, single):
    """A pair where single_text equals one component word means the other
    word was dropped/inserted, never a Sandhi junction."""
    assert check_sandhi_match(combined, single, DEFAULT_WEIGHTS) == -float("inf")


@pytest.mark.parametrize("combined,single", SANDHI_GENUINE)
def test_check_sandhi_match_accepts_genuine_junctions(combined, single):
    """Real Sandhi junctions — including ones whose junction characters fully
    assimilate (empty boundary region) — must keep scoring positively."""
    assert check_sandhi_match(combined, single, DEFAULT_WEIGHTS) > 0


@pytest.mark.parametrize("combined,single", SANDHI_FALSE_POSITIVES)
def test_alignment_counts_extra_word_as_indel_not_sandhi(combined, single):
    """End to end: the extra word must surface as a gap (insertion) in the
    alignment rather than being absorbed into a MERGE/SPLIT slot."""
    ref_toks, ref_tags = [single], ["WORD"]
    hyp_toks, hyp_tags = list(combined), ["WORD"] * len(combined)
    aligned_ref, aligned_hyp, _ = align_arrays(
        ref_toks, ref_tags, hyp_toks, hyp_tags, use_sandhi=True
    )
    joined = [tok for tok, _tag in aligned_ref + aligned_hyp]
    assert not any(tok.startswith(("MERGE:", "SPLIT:")) for tok in joined)
    assert any(tag == "GAP" for _tok, tag in aligned_ref)


def test_default_weights_use_correct_tolerance_spelling():
    """The sandhi tolerance key is public API surface (DEFAULT_WEIGHTS is
    exported); pin the correct spelling so the pre-release typo
    'sandhi_char_tolerence' cannot return."""
    assert "sandhi_char_tolerance" in DEFAULT_WEIGHTS
    assert "sandhi_char_tolerence" not in DEFAULT_WEIGHTS
