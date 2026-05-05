"""Golden cases that pin the headline claims of the SCRIBE paper.

These tests are the contract between the library's behavior and the
empirical claims made in the Interspeech 2026 paper. If any of these
fail, a published claim has regressed.
"""

import pytest

from scribe import text_error_rates

# Paper Figure 2: Malayalam sandhi-aware alignment
# Reference:  "ഇന്ന് അല്ലെങ്കിൽ നാളെയാകട്ടെ"  (3 word tokens)
# Hypothesis: "ഇന്നല്ലെങ്കിൽ നാളെ ആകട്ടെ"     (3 word tokens)
#
# A naive 1:1 aligner reports WER = 100% (every word is a substitution).
# SCRIBE's sandhi-aware alignment recognises:
#   - "ഇന്ന്" + "അല്ലെങ്കിൽ"  ->  "ഇന്നല്ലെങ്കിൽ"   (2:1 merge)
#   - "നാളെയാകട്ടെ"           ->  "നാളെ" + "ആകട്ടെ" (1:2 split)
# yielding ERlex = 0% with 2 sandhi corrections.
#
# This is the central empirical claim of the paper (Section 3.2,
# Figure 2). If this test fails, the headline result has regressed.
PAPER_FIG2_REF = "ഇന്ന് അല്ലെങ്കിൽ നാളെയാകട്ടെ"
PAPER_FIG2_HYP = "ഇന്നല്ലെങ്കിൽ നാളെ ആകട്ടെ"


def test_paper_fig2_sandhi_resolves_to_zero_lexical_error():
    """With sandhi enabled, the Fig. 2 case reports ERlex = 0%."""
    report = text_error_rates(PAPER_FIG2_REF, PAPER_FIG2_HYP, None, use_sandhi=True)
    word = report["WORD"]
    assert word["error_rate"] == 0.0
    assert word["substitutions"] == 0
    assert word["insertions"] == 0
    assert word["deletions"] == 0
    assert word["sandhi_hits"] == 2


def test_paper_fig2_without_sandhi_inflates_to_100_percent():
    """With sandhi disabled (1:1 alignment), the same case reports ERlex = 100%."""
    report = text_error_rates(PAPER_FIG2_REF, PAPER_FIG2_HYP, None, use_sandhi=False)
    word = report["WORD"]
    assert word["error_rate"] == 1.0
    # Three reference word tokens, every one substituted by the 1:1 aligner.
    assert word["substitutions"] == 3
    assert word["sandhi_hits"] == 0


def test_paper_fig2_only_word_category_is_affected():
    """The Malayalam case has no numerals or punctuation; those rates are 0."""
    report = text_error_rates(PAPER_FIG2_REF, PAPER_FIG2_HYP, None, use_sandhi=True)
    assert report["NUMERAL"]["error_rate"] == 0.0
    assert report["PUNCT"]["error_rate"] == 0.0


# Paper claim: domain-entity shielding keeps multi-character legal tokens
# (e.g. u/s, PW1, Ext.A) atomic, so a single-character ASR error inside
# them is counted in the domain category, not split into spurious
# punctuation/word errors. Without shielding, "u/s" would tokenise as
# three tokens ("u", "/", "s") and a sub of "u" -> "us" would explode
# into multiple error types.
@pytest.mark.parametrize(
    "ref,hyp,expected_legal_subs",
    [
        # u/s misrecognised as "us" -> single LEGAL substitution.
        ("charged u/s 302", "charged us 302", 1),
        # PW1 misrecognised as "PW2" -> single LEGAL substitution.
        ("witness PW1 testified", "witness PW2 testified", 1),
        # Exact match -> no errors.
        ("Ext.A is admitted", "Ext.A is admitted", 0),
    ],
)
def test_legal_domain_shielding_keeps_entities_atomic(legal_domain, ref, hyp, expected_legal_subs):
    report = text_error_rates(ref, hyp, legal_domain)
    assert report["LEGAL"]["substitutions"] == expected_legal_subs


def test_combined_denominator_keeps_sparse_categories_honest(legal_domain):
    """Paper §3.3: ER_t = (sub + ins + del) / N_comb, not N_t.

    Otherwise a single error in a 1-token category would show as 100%.
    Here, 1 LEGAL sub against a 4-token reference must report 1/4 = 25%
    LER, not 1/1 = 100%.
    """
    ref = "charged u/s 302 IPC"
    hyp = "charged us 302 IPC"
    report = text_error_rates(ref, hyp, legal_domain)
    # 1 legal entity ref-token, 2 word ref-tokens, 1 numeral ref-token = 4 total.
    # 1 LEGAL substitution. ER_legal = 1/4 = 0.25.
    assert report["LEGAL"]["substitutions"] == 1
    assert report["LEGAL"]["error_rate"] == pytest.approx(0.25)
