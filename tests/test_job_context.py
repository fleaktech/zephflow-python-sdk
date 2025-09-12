"""Tests for JobContext functionality and Java method invocation."""

from unittest.mock import Mock

import zephflow
from zephflow.job_context import DlqConfig, JobContext, S3DlqConfig


class TestJobContext:
    """Test JobContext creation and conversion."""

    def test_job_context_creation_empty(self):
        """Test creating an empty JobContext."""
        ctx = JobContext()
        assert ctx.other_properties == {}
        assert ctx.metric_tags == {}
        assert ctx.dlq_config is None

    def test_job_context_creation_with_params(self):
        """Test creating JobContext with parameters."""
        props = {"key": "value"}
        tags = {"env": "test"}
        dlq_config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)

        ctx = JobContext(props, tags, dlq_config)
        assert ctx.other_properties == props
        assert ctx.metric_tags == tags
        assert ctx.dlq_config == dlq_config

    def test_job_context_builder(self):
        """Test JobContext builder pattern."""
        dlq_config = S3DlqConfig("us-west-2", "my-bucket", 50, 2000)

        ctx = (
            JobContext.builder()
            .other_properties({"test": "value"})
            .metric_tags({"service": "test"})
            .dlq_config(dlq_config)
            .build()
        )

        assert ctx.other_properties == {"test": "value"}
        assert ctx.metric_tags == {"service": "test"}
        assert ctx.dlq_config == dlq_config

    def test_s3_dlq_config_creation(self):
        """Test S3DlqConfig creation."""
        config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)
        assert config.region == "us-east-1"
        assert config.bucket == "test-bucket"
        assert config.batch_size == 100
        assert config.flush_interval_millis == 5000
        assert isinstance(config, DlqConfig)


class TestJobContextJavaConversion:
    """Test JobContext to Java object conversion."""

    def test_job_context_to_java_conversion_empty(self):
        """Test converting empty JobContext to Java object."""
        # Create mocks for Java objects
        mock_gateway = Mock()
        mock_jvm = mock_gateway.jvm
        mock_java_job_context = Mock()
        mock_java_hashmap = Mock()

        # Set up JVM mocks
        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = mock_java_hashmap

        ctx = JobContext()
        ctx.to_java_object(mock_gateway)

        # Verify Java object creation
        mock_jvm.io.fleak.zephflow.api.JobContext.assert_called_once()

        # Verify empty HashMaps were set
        assert mock_java_job_context.setOtherProperties.call_count == 1
        assert mock_java_job_context.setMetricTags.call_count == 1

    def test_job_context_to_java_conversion_with_s3_dlq(self):
        """Test converting JobContext with S3DlqConfig to Java object."""
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

        dlq_config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)
        ctx = JobContext(
            other_properties={"key": "value"}, metric_tags={"env": "test"}, dlq_config=dlq_config
        )

        ctx.to_java_object(mock_gateway)

        # Verify Java S3DlqConfig was created and configured
        mock_jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig.assert_called_once()
        mock_java_s3_config.setRegion.assert_called_once_with("us-east-1")
        mock_java_s3_config.setBucket.assert_called_once_with("test-bucket")
        mock_java_s3_config.setBatchSize.assert_called_once_with(100)
        mock_java_s3_config.setFlushIntervalMillis.assert_called_once_with(5000)

        # Verify DLQ config was set on job context
        mock_java_job_context.setDlqConfig.assert_called_once_with(mock_java_s3_config)


class TestStartFlowWithJobContext:
    """Test start_flow method with JobContext parameter."""

    def test_start_flow_without_job_context(self):
        """Test that start_flow without JobContext calls startFlow()."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Set up the class-level gateway and jvm mocks
        original_gateway = zephflow.ZephFlow._gateway
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Test flow creation without job context
            flow = zephflow.ZephFlow.start_flow()

            assert flow is not None
            assert flow._java_flow == mock_java_flow

            # Verify the no-argument startFlow was called
            mock_java_zephflow_class.startFlow.assert_called_once_with()

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm

    def test_start_flow_with_python_job_context(self):
        """Test that start_flow with Python JobContext converts and calls startFlow(jobContext)."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Mock the Java JobContext creation
        mock_java_job_context = Mock()
        mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
        mock_jvm.java.util.HashMap.return_value = Mock()

        # Set up the class-level gateway and jvm mocks
        original_gateway = zephflow.ZephFlow._gateway
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Create a Python JobContext
            python_job_context = JobContext(
                other_properties={"test": "value"}, metric_tags={"env": "test"}
            )

            # Test flow creation with job context
            flow = zephflow.ZephFlow.start_flow(python_job_context)

            assert flow is not None
            assert flow._java_flow == mock_java_flow

            # Verify the JobContext was converted to Java and startFlow(jobContext) was called
            mock_java_zephflow_class.startFlow.assert_called_once_with(mock_java_job_context)

            # Verify Java JobContext was created
            mock_jvm.io.fleak.zephflow.api.JobContext.assert_called_once()

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm

    def test_start_flow_with_java_job_context(self):
        """Test start_flow with Java JobContext calls startFlow(jobContext)."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Set up the class-level gateway and jvm mocks
        original_gateway = zephflow.ZephFlow._gateway
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Create a mock Java JobContext (not a Python JobContext)
            mock_java_job_context = Mock()
            # Make isinstance(job_context, JobContext) return False
            mock_java_job_context.__class__ = Mock

            # Test flow creation with Java job context
            flow = zephflow.ZephFlow.start_flow(mock_java_job_context)

            assert flow is not None
            assert flow._java_flow == mock_java_flow

            # Verify startFlow(jobContext) was called directly with the Java object
            mock_java_zephflow_class.startFlow.assert_called_once_with(mock_java_job_context)

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm

    def test_start_flow_with_job_context_integration(self):
        """Integration test for start_flow with JobContext using the builder pattern."""
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
            # Create JobContext using builder pattern with S3 DLQ config
            dlq_config = S3DlqConfig("us-east-1", "test-bucket", 100, 5000)
            job_context = (
                JobContext.builder()
                .other_properties({"service": "test-service"})
                .metric_tags({"env": "production"})
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

            # Verify S3 config was set up correctly
            mock_java_s3_config.setRegion.assert_called_once_with("us-east-1")
            mock_java_s3_config.setBucket.assert_called_once_with("test-bucket")
            mock_java_s3_config.setBatchSize.assert_called_once_with(100)
            mock_java_s3_config.setFlushIntervalMillis.assert_called_once_with(5000)

            # Verify the DLQ config was set on the job context
            mock_java_job_context.setDlqConfig.assert_called_once_with(mock_java_s3_config)

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm


class TestJavaMethodSignatures:
    """Test that the correct Java method signatures are called."""

    def test_start_flow_method_signatures(self):
        """Test that start_flow calls the correct Java methods based on parameters."""
        # Mock the gateway setup
        mock_gateway = Mock()
        mock_jvm = Mock()
        mock_gateway.jvm = mock_jvm

        mock_java_zephflow_class = Mock()
        mock_jvm.io.fleak.zephflow.sdk.ZephFlow = mock_java_zephflow_class

        mock_java_flow = Mock()
        mock_java_zephflow_class.startFlow.return_value = mock_java_flow

        # Set up the class-level gateway and jvm mocks
        original_gateway = zephflow.ZephFlow._gateway
        original_jvm = zephflow.ZephFlow._jvm
        zephflow.ZephFlow._gateway = mock_gateway
        zephflow.ZephFlow._jvm = mock_jvm

        try:
            # Test 1: No parameters - should call startFlow()
            mock_java_zephflow_class.startFlow.reset_mock()
            zephflow.ZephFlow.start_flow()
            mock_java_zephflow_class.startFlow.assert_called_once_with()

            # Test 2: None parameter - should call startFlow()
            mock_java_zephflow_class.startFlow.reset_mock()
            zephflow.ZephFlow.start_flow(None)
            mock_java_zephflow_class.startFlow.assert_called_once_with()

            # Test 3: Python JobContext - should call startFlow(jobContext)
            mock_java_zephflow_class.startFlow.reset_mock()
            # Mock Java object creation for JobContext conversion
            mock_java_job_context = Mock()
            mock_jvm.io.fleak.zephflow.api.JobContext.return_value = mock_java_job_context
            mock_jvm.java.util.HashMap.return_value = Mock()

            python_job_context = JobContext()
            zephflow.ZephFlow.start_flow(python_job_context)
            mock_java_zephflow_class.startFlow.assert_called_once_with(mock_java_job_context)

            # Test 4: Java JobContext object - should call startFlow(jobContext) directly
            mock_java_zephflow_class.startFlow.reset_mock()
            java_job_context = Mock()
            java_job_context.__class__ = Mock  # Make isinstance check return False

            zephflow.ZephFlow.start_flow(java_job_context)
            mock_java_zephflow_class.startFlow.assert_called_once_with(java_job_context)

        finally:
            # Clean up the mocks
            zephflow.ZephFlow._gateway = original_gateway
            zephflow.ZephFlow._jvm = original_jvm


class TestJobContextExports:
    """Test that JobContext classes are properly exported."""

    def test_job_context_imports(self):
        """Test that JobContext classes can be imported from zephflow."""
        # Test that all JobContext classes are available at package level
        assert hasattr(zephflow, "JobContext")
        assert hasattr(zephflow, "JobContextBuilder")
        assert hasattr(zephflow, "DlqConfig")
        assert hasattr(zephflow, "S3DlqConfig")

        # Test they are the correct types
        assert zephflow.JobContext == JobContext
        assert zephflow.S3DlqConfig == S3DlqConfig

        # Test they can be used
        dlq_config = zephflow.S3DlqConfig("us-east-1", "test", 100, 5000)
        ctx = zephflow.JobContext.builder().dlq_config(dlq_config).build()
        assert isinstance(ctx, zephflow.JobContext)
        assert isinstance(dlq_config, zephflow.DlqConfig)
