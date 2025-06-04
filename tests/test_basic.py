"""Basic tests for ZephFlow Python SDK."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

import zephflow


class TestJarManager:
    """Test the JAR manager functionality."""

    def test_cache_dir_creation(self):
        """Test that cache directory is created properly."""
        manager = zephflow.JarManager()
        assert manager.cache_dir.exists()
        assert manager.cache_dir.is_dir()

    def test_env_override(self):
        """Test that environment variable override works."""
        # Create a temporary file to act as JAR
        with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
            temp_jar = f.name

        try:
            os.environ["ZEPHFLOW_MAIN_JAR"] = temp_jar
            manager = zephflow.JarManager()
            jar_path = manager.get_jar_path("0.2.1")
            assert jar_path == temp_jar
        finally:
            os.unlink(temp_jar)
            del os.environ["ZEPHFLOW_MAIN_JAR"]

    @patch("subprocess.run")
    def test_java_version_check(self, mock_run):
        """Test Java version checking."""
        # Mock Java 21 output
        mock_run.return_value = Mock(returncode=0, stderr='openjdk version "21.0.1" 2023-10-17')

        manager = zephflow.JarManager()
        # Should not raise an exception
        manager._check_java_version()

        # Mock Java 11 output (too old)
        mock_run.return_value = Mock(returncode=0, stderr='openjdk version "11.0.1" 2018-10-16')

        with pytest.raises(RuntimeError, match="Java 17 or higher is required"):
            manager._check_java_version()

    def test_version_cache(self, tmp_path):
        """Test version caching functionality."""
        manager = zephflow.JarManager()
        manager.cache_dir = tmp_path  # Override for testing
        manager.version_file = tmp_path / "version.json"

        # Initially no cache
        assert not manager._verify_cached_version("0.2.1")

        # Update cache
        manager._update_version_cache("0.2.1")

        # Now it should verify
        assert manager._verify_cached_version("0.2.1")
        assert not manager._verify_cached_version("0.4.0")


class TestZephFlowIntegration:
    """Integration tests for ZephFlow (use mocking since we can't start actual Java gateway)."""

    def test_start_flow(self):
        """Test creating a new flow."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Set up the class-level gateway and jvm mocks
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Test flow creation
            flow = zephflow.ZephFlow.start_flow()

            assert flow is not None
            assert flow._java_flow == mock_java_flow
            mock_java_zephflow_class.startFlow.assert_called_once()
        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = None
            zephflow.ZephFlow._jvm = None


class TestExamples:
    """Test that example code works (with mocking)."""

    def test_simple_example(self):
        """Test that the simple example pattern works."""
        # This mainly tests that the API calls are correct
        mock_java_flow = Mock()
        mock_java_flow.filter.return_value = mock_java_flow
        mock_java_flow.stdoutSink.return_value = mock_java_flow

        # Mock the JVM for encoding type lookup
        mock_jvm = Mock()
        mock_encoding_type = Mock()
        mock_jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf.return_value = mock_encoding_type

        # Set up the class-level jvm mock
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            with patch("zephflow.ZephFlow.start_flow") as mock_start:
                flow_instance = zephflow.ZephFlow(mock_java_flow)
                mock_start.return_value = flow_instance

                # Test the fluent API pattern
                flow = (
                    zephflow.ZephFlow.start_flow().filter("$.value > 10").stdout_sink("JSON_OBJECT")
                )

                assert flow is not None
                mock_java_flow.filter.assert_called_with("$.value > 10")
                mock_java_flow.stdoutSink.assert_called_with(mock_encoding_type)
        finally:
            # Clean up the mock
            zephflow.ZephFlow._jvm = original_jvm


def test_version():
    """Test that version is defined."""
    assert hasattr(zephflow, "__version__")
    assert isinstance(zephflow.__version__, str)
    # Check version format (basic check)
    assert "." in zephflow.__version__
