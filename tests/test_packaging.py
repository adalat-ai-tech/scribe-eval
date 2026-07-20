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
