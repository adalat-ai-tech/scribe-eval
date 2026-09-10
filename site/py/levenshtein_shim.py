"""Drop-in shim for the Levenshtein C extension inside Pyodide.

The demo page runs the real ``scribe`` wheel in the browser via Pyodide,
but Pyodide's package index carries neither ``Levenshtein`` nor its
``rapidfuzz`` backend. scribe consumes exactly two functions
(``align.py``, ``measure.py``), so this stdlib-only module is registered
as ``sys.modules["Levenshtein"]`` before the wheel is installed:

    distance(s1, s2) -> int
    editops(s1, s2)  -> list[tuple[str, int, int]]
                        # ('replace'|'delete'|'insert', src_pos, dest_pos)

Parity with the real package (Levenshtein 0.27.1):

- ``distance`` is the edit distance itself — a unique value, identical
  by construction (verified by fuzz tests in
  ``tests/test_levenshtein_shim.py``).
- ``len(editops(a, b)) == distance(a, b)`` holds for ANY minimal edit
  script, so every value scribe derives from the op count —
  ``cer_scribe`` and ``char_errors`` — is identical to the C extension
  regardless of backtrace tie-breaking.
- The S/I/D *composition* of a minimal script is not unique (e.g.
  "ab" -> "ba" costs 2 as two replaces or as one delete plus one
  insert). rapidfuzz's path recovery is not a fixed-preference
  Wagner-Fischer backtrace, so exact composition parity on adversarial
  strings is unattainable; the ordering used here — match when
  characters are equal, then delete > replace > insert — reproduces the
  real package's split on all natural-language pairs tested
  (Malayalam/Kannada/Hindi/English) and ~99% of random short strings,
  with the sum S+I+D always equal to the distance.

The file is deliberately named ``levenshtein_shim.py`` so it can never
shadow the real package during local CPython development or testing.
"""


def distance(s1: str, s2: str) -> int:
    """Levenshtein edit distance (unit costs), two-row Wagner-Fischer."""
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)
    if len(s2) > len(s1):
        s1, s2 = s2, s1
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        cur = [i]
        append = cur.append
        for j, c2 in enumerate(s2, 1):
            append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (c1 != c2)))
        prev = cur
    return prev[-1]


def editops(s1: str, s2: str) -> list:
    """Minimal edit script from s1 to s2 as (tag, src_pos, dest_pos) tuples.

    Position semantics follow Levenshtein 0.27.1: delete=(i-1, j),
    replace=(i-1, j-1), insert=(i, j-1). Ops are returned in ascending
    source order. Backtrace preference: match > delete > replace > insert
    (see module docstring for the tie-breaking analysis).
    """
    m, n = len(s1), len(s2)
    if m == 0:
        return [("insert", 0, j) for j in range(n)]
    if n == 0:
        return [("delete", i, 0) for i in range(m)]

    d = [list(range(n + 1))]
    for i in range(1, m + 1):
        row = [i] + [0] * n
        prev_row = d[i - 1]
        c1 = s1[i - 1]
        for j in range(1, n + 1):
            row[j] = min(
                prev_row[j] + 1,
                row[j - 1] + 1,
                prev_row[j - 1] + (c1 != s2[j - 1]),
            )
        d.append(row)

    ops = []
    i, j = m, n
    while i > 0 or j > 0:
        if i > 0 and j > 0 and s1[i - 1] == s2[j - 1] and d[i][j] == d[i - 1][j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("delete", i - 1, j))
            i -= 1
        elif i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + 1:
            ops.append(("replace", i - 1, j - 1))
            i -= 1
            j -= 1
        else:
            ops.append(("insert", i, j - 1))
            j -= 1
    ops.reverse()
    return ops
