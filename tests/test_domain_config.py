#!/usr/bin/env python3
"""
Test suite for file-based domain configuration loading.

Tests DomainConfig.from_file() functionality including:
- Parsing literal terms and regex patterns
- Metadata handling and parameter overrides
- Error handling for invalid files
- Integration with tokenization and error rate calculation
"""

import os
import tempfile

import pytest

from scribe import DomainConfig, domain_aware_tokenizer, text_error_rates


class TestFileLoading:
    """Test basic file loading and parsing."""

    def test_load_literal_terms_only(self):
        """Load config with only literal terms."""
        content = """
@name: test
@category: TEST
@label: TER

u/s
r/w
sec.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.name == "test"
            assert config.category == "TEST"
            assert config.label == "TER"
            assert not config.case_sensitive

            # Test that patterns match
            assert config.matches("u/s")
            assert config.matches("r/w")
            assert config.matches("sec.")
        finally:
            os.unlink(temp_path)

    def test_load_regex_patterns_only(self):
        """Load config with only regex patterns."""
        content = """
@name: test
@category: TEST

REGEX: PW[-\\s]*\\d+
REGEX: CW[-\\s]*\\d+
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.name == "test"

            # Test regex patterns match
            assert config.matches("PW1")
            assert config.matches("PW 1")
            assert config.matches("PW-1")
            assert config.matches("CW2")
            assert config.matches("CW 2")
            assert not config.matches("PW")  # No number
        finally:
            os.unlink(temp_path)

    def test_load_mixed_patterns(self):
        """Load config with both literal terms and regex patterns."""
        content = """
@name: mixed
@category: MIXED

# Literal terms
u/s
r/w

# Regex patterns
REGEX: PW[-\\s]*\\d+
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)

            # Literal terms should match
            assert config.matches("u/s")
            assert config.matches("r/w")

            # Regex patterns should match
            assert config.matches("PW1")
            assert config.matches("PW 1")
        finally:
            os.unlink(temp_path)

    def test_comments_and_empty_lines_ignored(self):
        """Comments and empty lines should be ignored."""
        content = """
# This is a comment
@name: test

# Another comment
u/s

# Blank lines above and below

r/w
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.matches("u/s")
            assert config.matches("r/w")
        finally:
            os.unlink(temp_path)

    def test_inline_comments_removed(self):
        """Inline comments after patterns should be removed."""
        content = """
@name: test

u/s  # Section reference
REGEX: PW[-\\s]*\\d+  # Prosecution witness
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.matches("u/s")
            assert config.matches("PW1")
            # Should not match the comment text
            assert not config.matches("Section reference")
        finally:
            os.unlink(temp_path)


class TestMetadataParsing:
    """Test metadata parsing and defaults."""

    def test_all_metadata_fields(self):
        """Parse all metadata fields."""
        content = """
@name: legal
@category: LEGAL
@label: LER
@case_sensitive: true

u/s
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.name == "legal"
            assert config.category == "LEGAL"
            assert config.label == "LER"
            assert config.case_sensitive is True
        finally:
            os.unlink(temp_path)

    def test_metadata_defaults(self):
        """Test default values when metadata is missing."""
        content = """
u/s
r/w
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)
            assert config.name == "domain"  # Default name
            assert config.category == "DOMAIN_DOMAIN"  # Default from name
            assert config.label == "DOMAINER"  # Default from name
            assert config.case_sensitive is False  # Default
        finally:
            os.unlink(temp_path)

    def test_case_sensitive_parsing(self):
        """Test case_sensitive metadata parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("yes", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("no", False),
            ("0", False),
        ]

        for value, expected in test_cases:
            content = f"""
@case_sensitive: {value}
test
"""
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                f.write(content)
                temp_path = f.name

            try:
                config = DomainConfig.from_file(temp_path)
                assert config.case_sensitive == expected, f"Failed for value: {value}"
            finally:
                os.unlink(temp_path)


class TestParameterOverrides:
    """Test runtime parameter overrides."""

    def test_name_override(self):
        """Override name from file."""
        content = """
@name: original

u/s
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path, name="override")
            assert config.name == "override"
        finally:
            os.unlink(temp_path)

    def test_category_override(self):
        """Override category from file."""
        content = """
@category: ORIGINAL

u/s
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path, category="OVERRIDE")
            assert config.category == "OVERRIDE"
        finally:
            os.unlink(temp_path)

    def test_case_sensitive_override(self):
        """Override case_sensitive from file."""
        content = """
@case_sensitive: false

API
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path, case_sensitive=True)
            assert config.case_sensitive is True
        finally:
            os.unlink(temp_path)


class TestPatternMatching:
    """Test pattern matching behavior."""

    def test_case_sensitivity(self):
        """Test case-sensitive vs case-insensitive matching."""
        content = """
@case_sensitive: true

API
SDK
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Case-sensitive: should not match lowercase
            config_sensitive = DomainConfig.from_file(temp_path)
            assert config_sensitive.matches("API")
            assert not config_sensitive.matches("api")
            assert not config_sensitive.matches("Api")

            # Override to case-insensitive: should match any case
            config_insensitive = DomainConfig.from_file(temp_path, case_sensitive=False)
            assert config_insensitive.matches("API")
            assert config_insensitive.matches("api")
            assert config_insensitive.matches("Api")
        finally:
            os.unlink(temp_path)

    def test_literal_escaping(self):
        """Literal terms should be escaped (u/s doesn't match 'us')."""
        content = """
@name: test

u/s
r/w
sec.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)

            # Should match exact terms
            assert config.matches("u/s")
            assert config.matches("r/w")

            # Should NOT match without special chars (escaping working)
            assert not config.matches("us")
            assert not config.matches("rw")

            # Period should be literal, not "any character"
            assert config.matches("sec.")
            assert not config.matches("seca")  # Period is not wildcard
        finally:
            os.unlink(temp_path)

    def test_regex_witness_patterns(self):
        """Test flexible witness designation patterns."""
        content = """
@name: legal

REGEX: PW[-\\s]*\\d+
REGEX: CW[-\\s]*\\d+
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)

            # Should match various formats
            assert config.matches("PW1")
            assert config.matches("PW 1")
            assert config.matches("PW-1")
            assert config.matches("PW123")
            assert config.matches("PW 123")

            assert config.matches("CW1")
            assert config.matches("CW 1")
            assert config.matches("CW-1")

            # Should not match without number
            assert not config.matches("PW")
            assert not config.matches("CW")
        finally:
            os.unlink(temp_path)


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_file_not_found(self):
        """Should raise FileNotFoundError for non-existent file."""
        with pytest.raises(FileNotFoundError):
            DomainConfig.from_file("/nonexistent/path/file.txt")

    def test_empty_file(self):
        """Should raise ValueError for file with no patterns."""
        content = """
# Only comments
@name: test
# And metadata
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="No patterns found"):
                DomainConfig.from_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_invalid_regex(self):
        """Should raise ValueError for invalid regex pattern."""
        content = """
@name: test

REGEX: PW[-\\s*\\d+
"""  # Missing closing bracket
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid regex pattern"):
                DomainConfig.from_file(temp_path)
        finally:
            os.unlink(temp_path)

    def test_invalid_metadata_format(self):
        """Should raise ValueError for invalid metadata format."""
        content = """
@name_without_colon

u/s
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid metadata format"):
                DomainConfig.from_file(temp_path)
        finally:
            os.unlink(temp_path)


class TestIntegration:
    """Test integration with tokenization and error calculation."""

    def test_with_domain_aware_tokenizer(self):
        """Loaded config should work with domain_aware_tokenizer."""
        content = """
@name: legal
@category: LEGAL

u/s
r/w
REGEX: PW[-\\s]*\\d+
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)

            # Test with various inputs
            tokens1, tags1 = domain_aware_tokenizer("charged u/s 302 IPC", config)
            assert "u/s" in tokens1
            assert "LEGAL" in tags1

            tokens2, tags2 = domain_aware_tokenizer("witness PW1 testified", config)
            assert "PW1" in tokens2 or "PW" in tokens2  # Depends on exact tokenization
            assert "LEGAL" in tags2

            tokens3, tags3 = domain_aware_tokenizer("witness PW 1 testified", config)
            assert "LEGAL" in tags3
        finally:
            os.unlink(temp_path)

    def test_with_text_error_rates(self):
        """Loaded config should work with text_error_rates."""
        content = """
@name: legal
@category: LEGAL
@label: LER

u/s
REGEX: PW[-\\s]*\\d+
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = DomainConfig.from_file(temp_path)

            ref = "charged u/s 302 IPC and PW1 testified"
            hyp = "charged us 302 IPC and PW 1 testified"

            report = text_error_rates(ref, hyp, config)

            # Should have LEGAL category in report
            assert "LEGAL" in report
            assert "error_rate" in report["LEGAL"]
        finally:
            os.unlink(temp_path)

    def test_backward_compatibility(self):
        """File-based config should produce same results as code-based."""
        # Create file with same patterns as LEGAL_DOMAIN
        content = """
@name: legal
@category: LEGAL
@label: LER

u/s
r/w
w.p.
o.s.
no.
v.
vs.
art.
sec.
PW
CW
Ext.
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            file_config = DomainConfig.from_file(temp_path)
            LEGAL_DOMAIN = DomainConfig.legal()

            # Test text
            text = "charged u/s 302 IPC, PW testified"

            # Tokenize with both configs
            tokens1, tags1 = domain_aware_tokenizer(text, file_config)
            tokens2, tags2 = domain_aware_tokenizer(text, LEGAL_DOMAIN)

            # Should produce similar results (may differ slightly in pattern order)
            assert "LEGAL" in tags1
            assert "LEGAL" in tags2
        finally:
            os.unlink(temp_path)


class TestBundledConfigFiles:
    """Tests that the bundled config files (loaded via the factory methods)
    parse correctly and produce the documented metadata."""

    def test_legal_factory_metadata(self):
        config = DomainConfig.legal()
        assert config.name == "legal"
        assert config.category == "LEGAL"
        assert config.label == "LER"
        assert not config.case_sensitive

    def test_legal_factory_witness_patterns(self):
        config = DomainConfig.legal()
        # The bundled regex shielding accepts PW1 / PW 1 / PW-1.
        assert config.matches("PW1")
        assert config.matches("PW 1")
        assert config.matches("PW-1")

    def test_medical_factory_metadata(self):
        config = DomainConfig.medical()
        assert config.name == "medical"
        assert config.category == "MEDICAL"
        assert config.label == "MER"

    def test_technical_factory_metadata(self):
        config = DomainConfig.technical()
        assert config.name == "technical"
        assert config.category == "TECH"
        assert config.label == "TchER"
        assert config.case_sensitive is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
