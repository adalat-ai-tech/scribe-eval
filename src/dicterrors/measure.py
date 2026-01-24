from .tokenize import legal_aware_tokenizer
from .align import align_arrays

def token_error_rates(aligned_ref, aligned_hyp):
    """
    aligned_ref: list of (text, tag)
    aligned_hyp: list of (text, tag)
    """
    categories = ["WORD", "PUNCT", "NUMERAL", "LEGAL"]
    stats = {cat: {"sub": 0, "ins": 0, "del": 0, "cor": 0, "total": 0, "sandhi": 0} for cat in categories}

    for (r_text, r_tag), (h_text, h_tag) in zip(aligned_ref, aligned_hyp):
        
        # 1. Handle Insertions (Gap in Reference)
        if r_text == "**":
            # We categorize the insertion error based on what the ASR hallucinated
            if h_tag in stats:
                stats[h_tag]["ins"] += 1
            continue

        # All other cases (Match, Sub, Del) are categorized by the REFERENCE tag
        if r_tag not in stats: continue
        curr = stats[r_tag]

        # 2. Handle Sandhi (Corrected Matches)
        if "MERGE:" in r_text:
            curr["total"] += 2  # A merge represents 2 original words
            curr["cor"] += 2
            curr["sandhi"] += 1
            continue
        
        if "SPLIT:" in h_text:
            curr["total"] += 1
            curr["cor"] += 1
            curr["sandhi"] += 1
            continue

        # 3. Standard Logic
        curr["total"] += 1
        if h_text == "**":
            curr["del"] += 1
        elif r_text == h_text:
            curr["cor"] += 1
        else:
            curr["sub"] += 1

    # Final calculations for the report
    report = {}
    for cat in categories:
        s = stats[cat]
        errors = s["sub"] + s["ins"] + s["del"]
        rate = errors / max(1, s["total"])
        report[cat] = {
            "error_rate": rate,
            "substitutions": s["sub"],
            "insertions": s["ins"],
            "deletions": s["del"],
            "correct": s["cor"],
            "total_ref": s["total"],
            "sandhi_hits": s["sandhi"]
        }
    
    return report

def text_error_rates(ref_text, hyp_text):
    t1, g1 = legal_aware_tokenizer(ref_text)
    t2, g2 = legal_aware_tokenizer(hyp_text)
    aligned_ref, aligned_hyp, _ = align_arrays(t1, g1, t2, g2)
    return token_error_rates(aligned_ref, aligned_hyp)