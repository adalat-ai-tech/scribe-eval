"""Guards on packaging metadata in pyproject.toml.

The bundled domain-config files must be enumerated explicitly in
package-data. A glob like "config/*.txt" would also package untracked
files sitting in a developer's working tree (e.g. gitignored
config/custom_*.txt wordlists), leaking them into published wheels.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent

BUNDLED_CONFIGS = {
    "config/legal_terms.txt",
    "config/medical_terms.txt",
    "config/technical_terms.txt",
}


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires Python 3.11+")
def test_package_data_enumerates_bundled_configs_explicitly():
    import tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)

    entries = pyproject["tool"]["setuptools"]["package-data"]["scribe"]

    for entry in entries:
        assert not any(ch in entry for ch in "*?["), (
            f"package-data entry {entry!r} is a glob; enumerate files explicitly "
            "so untracked files in a working tree cannot ship in the wheel"
        )

    assert set(entries) == BUNDLED_CONFIGS

    for entry in entries:
        assert (REPO_ROOT / "src" / "scribe" / entry).is_file(), (
            f"package-data lists {entry!r} but the file does not exist"
        )


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires Python 3.11+")
def test_dependency_layout():
    """matplotlib is core (charts are part of the batch workflow); the
    visualizer stays an extra and `all` bundles everything. There is no
    `charts` extra any more."""
    import tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)

    core = {dep.split(">=")[0].split("==")[0] for dep in pyproject["project"]["dependencies"]}
    assert "matplotlib" in core

    extras = pyproject["project"]["optional-dependencies"]
    assert "charts" not in extras
    assert any(dep.startswith("streamlit") for dep in extras["visualizer"])
    assert extras["all"] == ["scribe-eval[visualizer]"]


@pytest.mark.skipif(sys.version_info < (3, 11), reason="tomllib requires Python 3.11+")
def test_console_scripts():
    import tomllib

    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)

    scripts = pyproject["project"]["scripts"]
    assert scripts["scribe-batch"] == "scribe.batch_cli:main"
    assert scripts["scribe-visualizer"] == "scribe.visualizer.__main__:main"

    from scribe.batch_cli import main

    assert callable(main)
