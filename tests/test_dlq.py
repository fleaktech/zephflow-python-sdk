"""Tests for DLQ (Dead Letter Queue) functionality with Mock objects."""

from unittest.mock import Mock

import zephflow
from zephflow.job_context import JobContext, S3DlqConfig


class TestS3DlqConfig:
    """Test S3DlqConfig creation and configuration."""

    def test_s3_dlq_config_basic_creation(self):
        """Test creating S3DlqConfig with basic parameters."""
        config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)

        assert config.region == "us-east-1"
        assert config.bucket == "test-bucket"
        assert config.batch_size == 100
        assert config.flush_interval_millis == 5000
        assert config.access_key_id is None
        assert config.secret_access_key is None

    def test_s3_dlq_config_with_credentials(self):
        """Test creating S3DlqConfig with AWS credentials."""
        config = S3DlqConfig(
            region="us-west-2",
            bucket="dlq-bucket",
            batch_size=50,
            flush_interval_millis=3000,
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )

        assert config.region == "us-west-2"
        assert config.bucket == "dlq-bucket"
        assert config.batch_size == 50
        assert config.flush_interval_millis == 3000
        assert config.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_s3_dlq_config_partial_credentials(self):
        """Test creating S3DlqConfig with only access key (should work)."""
        config = S3DlqConfig(
            region="eu-west-1", bucket="dlq-bucket", access_key_id="AKIAIOSFODNN7EXAMPLE"
        )

        assert config.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.secret_access_key is None


class TestS3DlqJavaConversion:
    """Test S3DlqConfig to Java object conversion."""

    def test_s3_dlq_java_conversion_basic(self):
        """Test converting S3DlqConfig to Java object without credentials."""
        # Create mocks
        mock_gateway = Mock()
        mock_jvm = mock_gateway.jvm
        mock_java_job_context = Mock()
        mock_java_hashmap = Mock()
        mock_java_s3_config = Mock()

        # Set up JVM mocks
        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = mock_java_hashmap
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.return_value = mock_java_s3_config

        # Create JobContext with S3DlqConfig (no credentials)
        dlq_config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)
        ctx = JobContext(dlq_config=dlq_config)

        ctx.to_java_object(mock_gateway)

        # Verify Java S3DlqConfig was created and configured
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.assert_called_once()
        mock_java_s3_config.setRegion.assert_called_once_with("us-east-1")
        mock_java_s3_config.setBucket.assert_called_once_with("test-bucket")
        mock_java_s3_config.setBatchSize.assert_called_once_with(100)
        mock_java_s3_config.setFlushIntervalMillis.assert_called_once_with(5000)

        # Verify credentials were not set (since they are None)
        mock_java_s3_config.setAccessKeyId.assert_not_called()
        mock_java_s3_config.setSecretAccessKey.assert_not_called()

        # Verify DLQ config was set on job context
        mock_java_job_context.setDlqConfig.assert_called_once_with(mock_java_s3_config)

    def test_s3_dlq_java_conversion_with_credentials(self):
        """Test converting S3DlqConfig to Java object with credentials."""
        # Create mocks
        mock_gateway = Mock()
        mock_jvm = mock_gateway.jvm
        mock_java_job_context = Mock()
        mock_java_hashmap = Mock()
        mock_java_s3_config = Mock()

        # Set up JVM mocks
        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = mock_java_hashmap
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.return_value = mock_java_s3_config

        # Create JobContext with S3DlqConfig (with credentials)
        dlq_config = S3DlqConfig(
            region="us-west-2",
            bucket="dlq-bucket",
            batch_size=50,
            flush_interval_millis=3000,
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        ctx = JobContext(dlq_config=dlq_config)

        ctx.to_java_object(mock_gateway)

        # Verify Java S3DlqConfig was created and configured
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.assert_called_once()
        mock_java_s3_config.setRegion.assert_called_once_with("us-west-2")
        mock_java_s3_config.setBucket.assert_called_once_with("dlq-bucket")
        mock_java_s3_config.setBatchSize.assert_called_once_with(50)
        mock_java_s3_config.setFlushIntervalMillis.assert_called_once_with(3000)

        # Verify credentials were set
        mock_java_s3_config.setAccessKeyId.assert_called_once_with("AKIAIOSFODNN7EXAMPLE")
        mock_java_s3_config.setSecretAccessKey.assert_called_once_with(
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )

        # Verify DLQ config was set on job context
        mock_java_job_context.setDlqConfig.assert_called_once_with(mock_java_s3_config)

    def test_s3_dlq_java_conversion_partial_credentials(self):
        """Test converting S3DlqConfig to Java object with partial credentials."""
        # Create mocks
        mock_gateway = Mock()
        mock_jvm = mock_gateway.jvm
        mock_java_job_context = Mock()
        mock_java_hashmap = Mock()
        mock_java_s3_config = Mock()

        # Set up JVM mocks
        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = mock_java_hashmap
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.return_value = mock_java_s3_config

        # Create JobContext with S3DlqConfig (only access key)
        dlq_config = S3DlqConfig(
            region="eu-central-1", bucket="dlq-bucket", access_key_id="AKIAIOSFODNN7EXAMPLE"
        )
        ctx = JobContext(dlq_config=dlq_config)

        ctx.to_java_object(mock_gateway)

        # Verify credentials handling - only access key should be set
        mock_java_s3_config.setAccessKeyId.assert_called_once_with("AKIAIOSFODNN7EXAMPLE")
        mock_java_s3_config.setSecretAccessKey.assert_not_called()


class TestDlqIntegrationWithZephFlow:
    """Test DLQ configuration integration with ZephFlow."""

    def test_start_flow_with_dlq_config(self):
        """Test starting flow with DLQ configuration."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Mock all Java objects for JobContext conversion
        mock_java_job_context = Mock()
        mock_java_hashmap = Mock()
        mock_java_s3_config = Mock()

        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = mock_java_hashmap
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.return_value = mock_java_s3_config

        # Set up the class-level gateway and jvm mocks
        original_gateway = zephflow.ZephFlow._gateway
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Create comprehensive JobContext with DLQ configuration
            dlq_config = S3DlqConfig(
                region="us-east-1",
                bucket="app-dlq-bucket",
                batch_size=100,
                flush_interval_millis=5000,
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            )

            job_context = (
                JobContext.builder()
                .other_properties({"app": "data-processor"})
                .metric_tags({"env": "staging", "service": "data-pipeline"})
                .dlq_config(dlq_config)
                .build()
            )

            # Test flow creation
            flow = zephflow.ZephFlow.start_flow(job_context)

            assert flow is not None
            assert flow._java_flow == mock_java_flow

            # Verify the correct Java method was called
            mock_java_zephflow_class.startFlow.assert_called_once_with(mock_java_job_context)

            # Verify Java JobContext and S3DlqConfig were created and configured
            mock_jvm.io.fleak.zephflow.api.JobContext.assert_called_once()
            mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.assert_called_once()

            # Verify S3 DLQ config was set up correctly with credentials
            mock_java_s3_config.setRegion.assert_called_once_with("us-east-1")
            mock_java_s3_config.setBucket.assert_called_once_with("app-dlq-bucket")
            mock_java_s3_config.setBatchSize.assert_called_once_with(100)
            mock_java_s3_config.setFlushIntervalMillis.assert_called_once_with(5000)
            mock_java_s3_config.setAccessKeyId.assert_called_once_with("AKIAIOSFODNN7EXAMPLE")
            mock_java_s3_config.setSecretAccessKey.assert_called_once_with(
                "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            )

            # Verify the DLQ config was set on the job context
            mock_java_job_context.setDlqConfig.assert_called_once_with(mock_java_s3_config)

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm


class TestDlqExports:
    """Test that DLQ classes are properly exported."""

    def test_dlq_imports(self):
        """Test that DLQ classes can be imported from zephflow."""
        # Test that all DLQ classes are available at package level
        assert hasattr(zephflow, "S3DlqConfig")
        assert hasattr(zephflow, "DlqConfig")

        # Test they are the correct types
        assert zephflow.S3DlqConfig == S3DlqConfig

        # Test they can be used
        dlq_config = zephflow.S3DlqConfig(
            region="us-east-1",
            bucket="test-bucket",
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert isinstance(dlq_config, zephflow.DlqConfig)
        assert isinstance(dlq_config, zephflow.S3DlqConfig)
        assert dlq_config.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert dlq_config.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
