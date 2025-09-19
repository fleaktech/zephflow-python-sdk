from pathlib import Path

from zephflow import JobContext, S3DlqConfig, ZephFlow


class TestZephFlowIntegration:
    def test_process_from_yaml_dag(self):
        test_dir = Path(__file__).parent
        yaml_file_path = test_dir / "resources" / "test_dag.yaml"

        with open(yaml_file_path, "r") as file:
            file_content = file.read()
        print(file_content)
        flow = ZephFlow.from_yaml_dag(file_content)
        events = [
            {"id": 1, "value": 5, "name": "below_threshold"},
            {"id": 2, "value": 15, "name": "above_threshold"},
            {"id": 3, "value": 25, "name": "well_above_threshold"},
        ]

        result = flow.process(events)
        expected_outputs = [{"v": 5, "v2": 10.0}, {"v": 15, "v2": 30.0}, {"v": 25, "v2": 50.0}]

        expected_result = {
            "output_events": {"a": expected_outputs},
            "output_by_step": {"a": {"sync_input": expected_outputs}},
            "error_by_step": {},
            "sink_result_map": {},
        }
        assert result == expected_result

    def test_start_flow_without_job_context(self):
        """Test creating flow without JobContext (using defaults)"""
        # Create flow without JobContext - should use default values
        flow = ZephFlow.start_flow()

        # Build the same processing pipeline as with JobContext
        flow = flow.filter("$.value > 10").eval("dict(result=$.value * 2, original=$.value)")

        # Use the same test events
        test_events = [
            {"id": 1, "value": 5},  # Will be filtered out
            {"id": 2, "value": 15},  # Will pass through
            {"id": 3, "value": 25},  # Will pass through
            {"id": 4, "value": 8},  # Will be filtered out
            {"id": 5, "value": 30},  # Will pass through
        ]

        # Process events
        result = flow.process(test_events)

        # Verify basic processing works
        assert "output_events" in result
        assert "error_by_step" in result
        assert result["error_by_step"] == {}

        # Build DAG to verify default JobContext was created
        dag = flow.build_dag()
        java_job_context = dag.getJobContext()
        assert java_job_context is not None

        # Verify default metric tags were set
        metric_tags = java_job_context.getMetricTags()
        assert metric_tags.get("service") == "default_service"
        assert metric_tags.get("env") == "default_env"

        # Verify no DLQ config by default
        java_dlq_config = java_job_context.getDlqConfig()
        assert java_dlq_config is None

        print("Successfully verified flow without explicit JobContext uses defaults")

    def test_start_flow_with_job_context(self):
        """Test creating flow with custom JobContext including DLQ configuration"""
        # Configure DLQ
        dlq_config = S3DlqConfig(
            region="us-east-1", bucket="test-dlq-bucket", batch_size=100, flush_interval_millis=5000
        )

        # Create JobContext with custom configuration
        job_context = (
            JobContext.builder()
            .metric_tags({"env": "test", "service": "test-service"})
            .other_properties({"version": "1.0.0", "team": "data-platform"})
            .dlq_config(dlq_config)
            .build()
        )

        # Create flow with JobContext
        flow = ZephFlow.start_flow(job_context)

        # Build the same processing pipeline as without JobContext
        flow = flow.filter("$.value > 10").eval("dict(result=$.value * 2, original=$.value)")

        # Use the same test events
        test_events = [
            {"id": 1, "value": 5},  # Will be filtered out
            {"id": 2, "value": 15},  # Will pass through
            {"id": 3, "value": 25},  # Will pass through
            {"id": 4, "value": 8},  # Will be filtered out
            {"id": 5, "value": 30},  # Will pass through
        ]

        # Process events
        result = flow.process(test_events)

        # Verify processing results
        assert "output_events" in result
        assert "output_by_step" in result
        assert "error_by_step" in result

        # Check output events
        output_events = result["output_events"]
        if output_events:
            actual_outputs = list(output_events.values())[0] if output_events else []
            assert len(actual_outputs) == 3  # Only 3 events pass the filter

            # Verify transformation
            for output in actual_outputs:
                assert "result" in output
                assert "original" in output
                assert output["result"] == output["original"] * 2

        # Verify no errors
        assert result["error_by_step"] == {}

        # Build DAG to verify JobContext was properly configured
        dag = flow.build_dag()
        java_job_context = dag.getJobContext()
        assert java_job_context is not None

        # Verify custom metric tags
        metric_tags = java_job_context.getMetricTags()
        assert metric_tags.get("env") == "test"
        assert metric_tags.get("service") == "test-service"

        # Verify other properties
        other_props = java_job_context.getOtherProperties()
        assert other_props.get("version") == "1.0.0"
        assert other_props.get("team") == "data-platform"

        # Verify DLQ config
        java_dlq_config = java_job_context.getDlqConfig()
        assert java_dlq_config is not None
        assert java_dlq_config.getRegion() == "us-east-1"
        assert java_dlq_config.getBucket() == "test-dlq-bucket"
        assert java_dlq_config.getBatchSize() == 100
        assert java_dlq_config.getFlushIntervalMillis() == 5000

    def test_module_level_start_flow(self):
        """Test the module-level start_flow() convenience function with full processing pipeline"""
        import zephflow

        # Create flow using module-level convenience function
        flow = zephflow.start_flow()
        assert flow is not None
        assert isinstance(flow, zephflow.ZephFlow)

        # Build the same processing pipeline as other tests
        flow = flow.filter("$.value > 10").eval("dict(result=$.value * 2, original=$.value)")

        # Use the same test events
        test_events = [
            {"id": 1, "value": 5},  # Will be filtered out
            {"id": 2, "value": 15},  # Will pass through
            {"id": 3, "value": 25},  # Will pass through
            {"id": 4, "value": 8},  # Will be filtered out
            {"id": 5, "value": 30},  # Will pass through
        ]

        # Process events - this tests the full pipeline
        result = flow.process(test_events)

        # Verify basic processing works
        assert "output_events" in result
        assert "error_by_step" in result
        assert result["error_by_step"] == {}

        # Build DAG to verify the module-level function creates proper JobContext
        dag = flow.build_dag()
        java_job_context = dag.getJobContext()
        assert java_job_context is not None

        # Verify default metric tags were set (same as class method)
        metric_tags = java_job_context.getMetricTags()
        assert metric_tags.get("service") == "default_service"
        assert metric_tags.get("env") == "default_env"

        # Verify no DLQ config by default
        java_dlq_config = java_job_context.getDlqConfig()
        assert java_dlq_config is None

        print("Successfully verified module-level start_flow() with full processing pipeline")
