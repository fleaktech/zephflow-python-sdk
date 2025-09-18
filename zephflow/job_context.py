from abc import ABC
from typing import Any, Dict, Optional


class DlqConfig(ABC):
    """Abstract base class for Dead Letter Queue configuration."""

    pass


class S3DlqConfig(DlqConfig):
    """S3-based Dead Letter Queue configuration."""

    def __init__(
        self,
        region: str,
        bucket: str,
        batch_size: int = 100,
        flush_interval_millis: int = 5000,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
    ):
        """
        Initialize S3 DLQ configuration.

        Args:
            region: AWS region
            bucket: S3 bucket name
            batch_size: Batch size for DLQ operations
            flush_interval_millis: Flush interval in milliseconds
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
        """
        self.region = region
        self.bucket = bucket
        self.batch_size = batch_size
        self.flush_interval_millis = flush_interval_millis
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key


class JobContext:
    """
    Job context for ZephFlow operations.

    This class holds configuration and metadata for job execution,
    including custom properties, metric tags, and DLQ configuration.
    """

    def __init__(
        self,
        other_properties: Optional[Dict[str, Any]] = None,
        metric_tags: Optional[Dict[str, str]] = None,
        dlq_config: Optional[DlqConfig] = None,
    ):
        """
        Initialize JobContext.

        Args:
            other_properties: Additional properties for the job context
            metric_tags: Tags for metrics collection
            dlq_config: Dead Letter Queue configuration
        """
        self.other_properties = other_properties or {}
        self.metric_tags = metric_tags or {}
        self.dlq_config = dlq_config

    @classmethod
    def builder(cls):
        """
        Create a builder for JobContext.

        Returns:
            JobContextBuilder: A builder instance
        """
        return JobContextBuilder()

    def to_java_object(self, gateway):
        """
        Convert to Java JobContext object.

        Args:
            gateway: The Java gateway instance

        Returns:
            Java JobContext object
        """
        java_job_context = gateway.jvm.io.fleak.zephflow.api.JobContext()

        # Set other properties
        java_other_properties = gateway.jvm.java.util.HashMap()
        for key, value in self.other_properties.items():
            java_other_properties.put(key, value)
        java_job_context.setOtherProperties(java_other_properties)

        # Set metric tags
        java_metric_tags = gateway.jvm.java.util.HashMap()
        for key, value in self.metric_tags.items():
            java_metric_tags.put(key, value)
        java_job_context.setMetricTags(java_metric_tags)

        # Set DLQ config if provided
        if self.dlq_config:
            if isinstance(self.dlq_config, S3DlqConfig):
                java_s3_config = gateway.jvm.io.fleak.zephflow.api.JobContext.S3DlqConfig()
                java_s3_config.setRegion(self.dlq_config.region)
                java_s3_config.setBucket(self.dlq_config.bucket)
                java_s3_config.setBatchSize(self.dlq_config.batch_size)
                java_s3_config.setFlushIntervalMillis(self.dlq_config.flush_interval_millis)
                if self.dlq_config.access_key_id is not None:
                    java_s3_config.setAccessKeyId(self.dlq_config.access_key_id)
                if self.dlq_config.secret_access_key is not None:
                    java_s3_config.setSecretAccessKey(self.dlq_config.secret_access_key)
                java_job_context.setDlqConfig(java_s3_config)

        return java_job_context


class JobContextBuilder:
    """Builder pattern for JobContext."""

    def __init__(self):
        self._other_properties = {}
        self._metric_tags = {}
        self._dlq_config = None

    def other_properties(self, properties: Dict[str, Any]):
        """
        Set other properties.

        Args:
            properties: Dictionary of additional properties

        Returns:
            JobContextBuilder: This builder instance
        """
        self._other_properties = properties
        return self

    def metric_tags(self, tags: Dict[str, str]):
        """
        Set metric tags.

        Args:
            tags: Dictionary of metric tags

        Returns:
            JobContextBuilder: This builder instance
        """
        self._metric_tags = tags
        return self

    def dlq_config(self, config: DlqConfig):
        """
        Set DLQ configuration.

        Args:
            config: DLQ configuration

        Returns:
            JobContextBuilder: This builder instance
        """
        self._dlq_config = config
        return self

    def build(self) -> JobContext:
        """
        Build the JobContext.

        Returns:
            JobContext: The constructed JobContext instance
        """
        return JobContext(
            other_properties=self._other_properties.copy(),
            metric_tags=self._metric_tags.copy(),
            dlq_config=self._dlq_config,
        )
