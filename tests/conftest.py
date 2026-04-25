"""Shared pytest fixtures for the scribe-eval test suite."""

import pytest

from scribe import DomainConfig


@pytest.fixture
def legal_domain():
    """Bundled legal domain config (u/s, r/w, PW1, Ext.A, etc.)."""
    return DomainConfig.legal()


@pytest.fixture
def medical_domain():
    """Bundled medical domain config (mg, ml, dosages, etc.)."""
    return DomainConfig.medical()


@pytest.fixture
def technical_domain():
    """Bundled technical domain config (API, SDK, v1.0, etc.)."""
    return DomainConfig.technical()
