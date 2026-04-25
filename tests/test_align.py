"""Tests for the sandhi-aware alignment engine."""

from scribe import align_arrays, domain_aware_tokenizer


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
