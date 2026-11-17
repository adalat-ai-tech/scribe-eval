"""Tests for the ``scribe-batch`` command (``scribe.batch_cli``).

The CLI is exercised in-process through ``main([...])`` so argument
parsing, file output and console echo are all covered without spawning
subprocesses, except for two smoke tests of the real entry points.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scribe import batch_cli
from scribe.batch_cli import (
    CONSOLE_ROW_CAP,
    build_parser,
    format_analysis_report,
    main,
    parse_top_n,
    parse_workers,
    resolve_workers,
)

REPO_ROOT = Path(__file__).parent.parent
SAMPLE = REPO_ROOT / "examples" / "predictions.jsonl"
EXAMPLE_SCRIPT = REPO_ROOT / "examples" / "batch_evaluate.py"

OUTPUT_FILES = {"summary_report.txt", "evaluation-detailed.jsonl"}
ANALYSIS_FILES = OUTPUT_FILES | {"analysis_report.txt"}


def run(tmp_path, *extra, input_file=SAMPLE):
    """Run the CLI on ``input_file`` into ``tmp_path`` and return the exit code."""
    return main(["--input", str(input_file), "--output-dir", str(tmp_path), *extra])


def summary_text(tmp_path):
    return (tmp_path / "summary_report.txt").read_text(encoding="utf-8")


def analysis_text(tmp_path):
    return (tmp_path / "analysis_report.txt").read_text(encoding="utf-8")


def table_rows(text, heading_suffix):
    """Numbered rows of the frequent-error table whose heading ends with ``heading_suffix``."""
    section = text.split(heading_suffix)[1].split("\n\n")[0]
    return [line for line in section.splitlines() if line.strip()[:1].isdigit()]


def sandhi_column_total(summary):
    """Sum of the SANDHI column over the OVERALL row of a summary report."""
    for line in summary.splitlines():
        if line.startswith("OVERALL"):
            return int(line.split("|")[-1])
    raise AssertionError("no OVERALL row in summary")


# --------------------------------------------------------------------------
# Argument types
# --------------------------------------------------------------------------


def test_top_n_accepts_int_or_all():
    assert parse_top_n("15") == 15
    assert parse_top_n("all") is None
    assert parse_top_n("ALL") is None
    for bad in ("0", "-3", "ten", ""):
        with pytest.raises(Exception):
            parse_top_n(bad)


def test_workers_accepts_int_or_auto():
    assert parse_workers("4") == 4
    assert parse_workers("auto") is None
    for bad in ("0", "many"):
        with pytest.raises(Exception):
            parse_workers(bad)


def test_parser_defaults_are_all_and_auto():
    args = build_parser().parse_args(["--input", "x.jsonl"])
    assert args.top_n is None
    assert args.workers is None
    assert args.no_sandhi is False
    assert args.group_by == "source_dataset"
    assert args.output_dir == "scribe-output"


def test_input_is_required_without_a_default(capsys):
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2
    assert "--input" in capsys.readouterr().err


def test_input_default_can_be_supplied():
    args = build_parser(default_input="bundled.jsonl", default_output="out").parse_args([])
    assert args.input == "bundled.jsonl"
    assert args.output_dir == "out"


def test_resolve_workers_auto_is_min_of_cpus_and_samples(monkeypatch):
    monkeypatch.setattr(batch_cli, "usable_cpu_count", lambda: 8)
    assert resolve_workers(None, 3) == 3
    assert resolve_workers(None, 100) == 8
    assert resolve_workers(None, 0) == 1
    # Explicit values pass through, even above the CPU count.
    assert resolve_workers(32, 3) == 32


def test_usable_cpu_count_is_positive():
    assert batch_cli.usable_cpu_count() >= 1


# --------------------------------------------------------------------------
# End-to-end runs
# --------------------------------------------------------------------------


def test_end_to_end_analysis_with_sandhi_off(tmp_path, capsys):
    code = run(tmp_path, "--analysis", "--top-n", "3", "--no-sandhi", "--workers", "2")
    assert code == 0
    assert ANALYSIS_FILES <= {p.name for p in tmp_path.iterdir()}

    summary = summary_text(tmp_path)
    assert sandhi_column_total(summary) == 0
    run_info = summary.strip().splitlines()[-1]
    assert run_info.startswith("Evaluation completed in")
    assert "workers=2" in run_info
    assert "sandhi=off" in run_info
    assert "top_n=3" in run_info

    report = analysis_text(tmp_path)
    assert "Sandhi" not in report  # no merge/split sections when detection is off
    assert "--- Top 3 Frequent Substitutions ---" in report

    out = capsys.readouterr().out
    assert "Sandhi detection: disabled" in out
    assert run_info in out


def test_sandhi_on_by_default_counts_hits(tmp_path):
    assert run(tmp_path, "--workers", "1") == 0
    with_sandhi = sandhi_column_total(summary_text(tmp_path))
    assert run(tmp_path, "--workers", "1", "--no-sandhi") == 0
    without = sandhi_column_total(summary_text(tmp_path))
    assert with_sandhi > 0
    assert without == 0


def test_top_n_all_fills_file_and_caps_console(tmp_path, capsys):
    assert run(tmp_path, "--analysis", "--workers", "1") == 0
    report = analysis_text(tmp_path)
    out = capsys.readouterr().out

    # The bundled sample has more distinct substitutions than the console cap.
    file_rows = table_rows(report, "Frequent Substitutions ---")
    assert len(file_rows) > CONSOLE_ROW_CAP
    assert f"--- All {len(file_rows)} Frequent Substitutions ---" in report
    assert "more rows in" not in report

    console_rows = table_rows(out, "Frequent Substitutions ---")
    assert len(console_rows) == CONSOLE_ROW_CAP
    assert f"--- Top {CONSOLE_ROW_CAP} Frequent Substitutions ---" in out
    assert f"({len(file_rows) - CONSOLE_ROW_CAP} more rows in analysis_report.txt)" in out


def test_explicit_top_n_matches_on_console_and_file(tmp_path, capsys):
    assert run(tmp_path, "--analysis", "--top-n", "5", "--workers", "1") == 0
    report = analysis_text(tmp_path)
    out = capsys.readouterr().out
    assert "--- Top 5 Frequent Substitutions ---" in report
    assert "--- Top 5 Frequent Substitutions ---" in out
    assert "more rows in" not in out


def test_workers_auto_is_reported(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(batch_cli, "usable_cpu_count", lambda: 2)
    assert run(tmp_path) == 0
    out = capsys.readouterr().out
    assert "Workers: 2 (auto)" in out
    assert "workers=2" in summary_text(tmp_path)


def test_group_by_custom_field(tmp_path):
    records = [
        '{"text": "hello world", "pred_text": "hello world", "speaker": "a"}',
        '{"text": "charged u/s 302", "pred_text": "charged us 302", "speaker": "b"}',
    ]
    src = tmp_path / "in.jsonl"
    src.write_text("\n".join(records) + "\n", encoding="utf-8")
    out_dir = tmp_path / "out"
    assert run(out_dir, "--group-by", "speaker", "--workers", "1", input_file=src) == 0
    summary = summary_text(out_dir)
    assert "GROUP" in summary
    assert "\na " in summary and "\nb " in summary


def test_chart_is_written(tmp_path):
    pytest.importorskip("matplotlib")
    assert run(tmp_path, "--analysis", "--chart", "--workers", "1") == 0
    assert (tmp_path / "category_breakdown.png").stat().st_size > 0


def test_chart_without_analysis_warns(tmp_path, capsys):
    assert run(tmp_path, "--chart", "--workers", "1") == 0
    assert "--chart needs --analysis" in capsys.readouterr().err
    assert not (tmp_path / "category_breakdown.png").exists()


def test_missing_input_returns_1(tmp_path, capsys):
    assert run(tmp_path, input_file=tmp_path / "nope.jsonl") == 1
    assert "Input file not found" in capsys.readouterr().err


def test_unknown_domain_returns_1(tmp_path, capsys):
    assert run(tmp_path, "--domain", "astrology") == 1
    assert "neither a bundled domain" in capsys.readouterr().err


def test_bad_record_hint_and_skip(tmp_path, capsys):
    src = tmp_path / "dirty.jsonl"
    src.write_text(
        '{"text": "ok", "pred_text": "ok"}\nnot json\n',
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    assert run(out_dir, "--workers", "1", input_file=src) == 1
    assert "--skip-bad-records" in capsys.readouterr().err
    assert run(out_dir, "--workers", "1", "--skip-bad-records", input_file=src) == 0


# --------------------------------------------------------------------------
# Report formatting
# --------------------------------------------------------------------------


def _summary_with(n_subs):
    subs = [(f"r{i}", f"h{i}", n_subs - i) for i in range(n_subs)]
    return {
        "wer_scribe": 0.1,
        "total_correct_pct": 90.0,
        "contributions": {},
        "frequent_substitutions": {"_all": subs},
        "frequent_deletions": {"_all": []},
        "frequent_insertions": {"_all": []},
        "frequent_sandhi_merges": {"_all": []},
        "frequent_sandhi_splits": {"_all": []},
    }


def test_format_analysis_report_headings():
    summary = _summary_with(25)
    full = format_analysis_report(summary, None)
    assert "--- All 25 Frequent Substitutions ---" in full
    assert "Frequent Deletions" not in full  # empty tables are omitted
    assert full.endswith("=" * 85 + "\n")

    capped = format_analysis_report(summary, None, console_cap=20)
    assert "--- Top 20 Frequent Substitutions ---" in capped
    assert "(5 more rows in analysis_report.txt)" in capped

    # A cap that is not reached keeps the "All" heading and adds no note.
    assert "--- All 25 Frequent Substitutions ---" in format_analysis_report(
        summary, None, console_cap=30
    )

    cut = format_analysis_report(summary, 10, cer_scribe=0.05)
    assert "| 5.00% CER_SCRIBE" in cut
    assert "--- Top 10 Frequent Substitutions ---" in cut
    assert len(table_rows(cut, "Frequent Substitutions ---")) == 10


# --------------------------------------------------------------------------
# Real entry points
# --------------------------------------------------------------------------


def _subprocess(args, cwd):
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)


def test_python_m_entry_point(tmp_path):
    proc = _subprocess(
        [
            sys.executable,
            "-m",
            "scribe.batch_cli",
            "--input",
            str(SAMPLE),
            "--output-dir",
            str(tmp_path),
            "--workers",
            "1",
        ],
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "summary_report.txt").exists()


def test_examples_wrapper_uses_bundled_defaults(tmp_path):
    proc = _subprocess(
        [sys.executable, str(EXAMPLE_SCRIPT), "--output-dir", str(tmp_path), "--workers", "1"],
        cwd=tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    assert OUTPUT_FILES <= {p.name for p in tmp_path.iterdir()}
