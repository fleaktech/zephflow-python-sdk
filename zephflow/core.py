import json
import os
import sys
import uuid
from typing import Any, Dict, Optional

from py4j.java_gateway import GatewayParameters, JavaGateway, launch_gateway

from .jar_manager import JarManager
from .utils import convert_result_to_python, is_json, read_file


class ZephFlow:
    """
    A Python client for ZephFlow data processing pipelines.

    This class provides a fluent API for building and executing data processing
    flows using the underlying Java ZephFlow SDK.
    """

    # Singleton gateway
    _gateway = None
    _jvm = None
    _jar_manager = JarManager()

    @staticmethod
    def _ensure_gateway():
        """Ensure the Java gateway is initialized."""
        if ZephFlow._gateway is None:
            # Get JAR path from jar manager or environment
            main_jar_path = os.environ.get("ZEPHFLOW_MAIN_JAR")

            if not main_jar_path:
                # Download JAR if needed - use default Java SDK version
                main_jar_path = ZephFlow._jar_manager.get_jar_path()

            # Get additional classpath if provided
            deps_classpath = os.environ.get("ZEPHFLOW_DEPS_CLASSPATH", "")

            # Combine classpath elements
            classpath = main_jar_path
            if deps_classpath:
                classpath = f"{main_jar_path}{os.pathsep}{deps_classpath}"

            print(f"Using classpath: {classpath}")

            # Launch returns port number
            port = launch_gateway(
                classpath=classpath,
                die_on_exit=True,
                redirect_stdout=sys.stdout,
                redirect_stderr=sys.stderr,
            )

            # Create gateway connection
            ZephFlow._gateway = JavaGateway(gateway_parameters=GatewayParameters(port=port))
            ZephFlow._jvm = ZephFlow._gateway.jvm

    @staticmethod
    def from_yaml_dag(yaml_dag: str, metrics_provider: Any = None):
        ZephFlow._ensure_gateway()
        assert ZephFlow._jvm is not None  # Tell mypy that _jvm is not None
        java_zephflow_class = ZephFlow._jvm.io.fleak.zephflow.sdk.ZephFlow
        return ZephFlow(java_zephflow_class.fromYamlDag(yaml_dag, metrics_provider))

    @staticmethod
    def start_flow():
        """
        Start a new ZephFlow instance with default settings.

        Returns:
            ZephFlow: A new ZephFlow instance

        Example:
            >>> import zephflow
            >>> flow = zephflow.ZephFlow.start_flow()
            >>> flow = flow.filter("$.value > 10").stdout_sink("JSON_OBJECT")
        """
        ZephFlow._ensure_gateway()

        # Get Java ZephFlow class
        java_zephflow_class = ZephFlow._jvm.io.fleak.zephflow.sdk.ZephFlow
        java_flow = java_zephflow_class.startFlow()

        return ZephFlow(java_flow)

    @staticmethod
    def execute_dag(
        dag: Any, job_id: str = "", env: str = "", service: str = "", metrics_provider: Any = None
    ):
        """
        Execute a ZephFlow DAG.

        Args:
            dag: The DAG can be a JSON or YAML file path, an AdjacencyListDagDefinition instance,
                 or a string with the JSON or YAML DAG content.
            job_id: Optional job ID.
            env: Optional environment (default from ZEPHFLOW_ENV).
            service: Optional service name (default from ZEPHFLOW_SERVICE).
            metrics_provider: Optional metrics provider.
        """

        ZephFlow._ensure_gateway()
        java_zephflow_class = (
            ZephFlow._jvm.io.fleak.zephflow.sdk.ZephFlow  # type: ignore[attr-defined]
        )

        job_id = job_id or str(uuid.uuid4())
        env = env or os.environ.get("ZEPHFLOW_ENV", "default")
        service = service or os.environ.get("ZEPHFLOW_SERVICE", "default")

        if (
            hasattr(dag, "getClass")
            and dag.getClass().getName()
            == "io.fleak.zephflow.runner.dag.AdjacencyListDagDefinition"
        ):
            java_zephflow_class.executeDag(job_id, env, service, dag, metrics_provider)
        else:
            dag = str(dag)

            if dag.endswith((".yaml", ".yml")):
                java_zephflow_class.executeYamlDag(
                    job_id, env, service, read_file(dag), metrics_provider
                )
            elif dag.endswith(".json"):
                java_zephflow_class.executeJsonDag(
                    job_id, env, service, read_file(dag), metrics_provider
                )
            elif is_json(dag):
                java_zephflow_class.executeJsonDag(job_id, env, service, dag, metrics_provider)
            else:
                # Assume JSON if not YAML
                java_zephflow_class.executeYamlDag(job_id, env, service, dag, metrics_provider)

    @staticmethod
    def merge(*flows):
        """
        Merge multiple flows into a single flow.

        Args:
            *flows: ZephFlow instances to merge

        Returns:
            ZephFlow: A new ZephFlow instance representing the merged flow

        Example:
            >>> flow1 = zephflow.ZephFlow.start_flow().filter("$.type == 'A'")
            >>> flow2 = zephflow.ZephFlow.start_flow().filter("$.type == 'B'")
            >>> merged = zephflow.ZephFlow.merge(flow1, flow2)
        """
        ZephFlow._ensure_gateway()

        # Convert Python ZephFlow objects to Java ZephFlow objects
        java_flows = ZephFlow._gateway.new_array(
            ZephFlow._jvm.io.fleak.zephflow.sdk.ZephFlow, len(flows)
        )

        for i, flow in enumerate(flows):
            java_flows[i] = flow._java_flow

        # Call static merge method
        java_zephflow_class = ZephFlow._jvm.io.fleak.zephflow.sdk.ZephFlow
        merged_java_flow = java_zephflow_class.merge(java_flows)

        return ZephFlow(merged_java_flow)

    def __init__(self, java_flow_obj):
        """Initialize a ZephFlow instance with a Java flow object."""
        self._java_flow = java_flow_obj

    def filter(self, condition: str):
        """
        Add a filter operation to the flow.

        Args:
            condition: A string expression to filter events

        Returns:
            ZephFlow: A new ZephFlow instance with the filter added
        """
        new_java_flow = self._java_flow.filter(condition)
        return ZephFlow(new_java_flow)

    def assertion(self, condition: str):
        """
        Add an assertion operation to the flow. Events that don't match
        the condition will throw an exception.

        Args:
            condition: A string expression for the assertion

        Returns:
            ZephFlow: A new ZephFlow instance with the assertion added
        """
        new_java_flow = self._java_flow.assertion(condition)
        return ZephFlow(new_java_flow)

    def parse(self, parser_config: Dict[str, Any]):
        """
        Add a parser operation to the flow.

        Args:
            parser_config: Dict containing parser configuration

        Returns:
            ZephFlow: A new ZephFlow instance with the parser added
        """
        # Convert Python dict to JSON string
        json_str = json.dumps(parser_config)

        # Use appendNode with the parser command name and JSON config string
        new_java_flow = self._java_flow.appendNode("parser", json_str)
        return ZephFlow(new_java_flow)

    def stdin_source(self, encoding_type: str):
        """
        Add a standard input source to the flow.

        Args:
            encoding_type: Encoding type for the input (e.g., "JSON_OBJECT")

        Returns:
            ZephFlow: A new ZephFlow instance with the source added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )
        new_java_flow = self._java_flow.stdinSource(java_encoding_type)
        return ZephFlow(new_java_flow)

    def file_source(self, file_path: str, encoding_type: str):
        """
        Add a file source to the flow.

        Args:
            file_path: Path to the source file
            encoding_type: Encoding type for the file (e.g., "JSON_OBJECT")

        Returns:
            ZephFlow: A new ZephFlow instance with the source added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )
        new_java_flow = self._java_flow.fileSource(file_path, java_encoding_type)
        return ZephFlow(new_java_flow)

    def eval(self, eval_expression: str):
        """
        Add an evaluation operation to the flow.

        Args:
            eval_expression: Expression to evaluate

        Returns:
            ZephFlow: A new ZephFlow instance with the evaluation added
        """
        new_java_flow = self._java_flow.eval(eval_expression)
        return ZephFlow(new_java_flow)

    def sql(self, sql_query: str):
        """
        Add a SQL evaluation operation to the flow.

        Args:
            sql_query: SQL query to execute

        Returns:
            ZephFlow: A new ZephFlow instance with the SQL evaluation added
        """
        new_java_flow = self._java_flow.sql(sql_query)
        return ZephFlow(new_java_flow)

    def s3_sink(
        self,
        region: str,
        bucket: str,
        folder: str,
        encoding_type: str,
        s3_endpoint_override: Optional[str] = None,
    ):
        """
        Add an S3 sink to the flow.

        Args:
            region: AWS region
            bucket: S3 bucket name
            folder: Folder path within the bucket
            encoding_type: Encoding type for the output (e.g., "JSON_OBJECT")
            s3_endpoint_override: Optional endpoint override for S3 compatibility

        Returns:
            ZephFlow: A new ZephFlow instance with the S3 sink added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )

        if s3_endpoint_override:
            new_java_flow = self._java_flow.s3Sink(
                region, bucket, folder, java_encoding_type, s3_endpoint_override
            )
        else:
            new_java_flow = self._java_flow.s3Sink(region, bucket, folder, java_encoding_type)

        return ZephFlow(new_java_flow)

    def kafka_source(
        self,
        broker: str,
        topic: str,
        group_id: str,
        encoding_type: str,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Add a Kafka source to the flow.

        Args:
            broker: Kafka broker address
            topic: Kafka topic name
            group_id: Consumer group ID
            encoding_type: Encoding type for the input (e.g., "JSON_OBJECT")
            properties: Optional additional Kafka properties

        Returns:
            ZephFlow: A new ZephFlow instance with the Kafka source added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )

        # Convert properties dict to Java Map
        java_properties = None
        if properties:
            java_properties = ZephFlow._gateway.jvm.java.util.HashMap()
            for k, v in properties.items():
                java_properties.put(k, v)

        new_java_flow = self._java_flow.kafkaSource(
            broker, topic, group_id, java_encoding_type, java_properties
        )
        return ZephFlow(new_java_flow)

    def kafka_sink(
        self,
        broker: str,
        topic: str,
        partition_key_field_expr: Optional[str],
        encoding_type: str,
        properties: Optional[Dict[str, str]] = None,
    ):
        """
        Add a Kafka sink to the flow.

        Args:
            broker: Kafka broker address
            topic: Kafka topic name
            partition_key_field_expr: Expression to extract partition key
            encoding_type: Encoding type for the output (e.g., "JSON_OBJECT")
            properties: Optional additional Kafka properties

        Returns:
            ZephFlow: A new ZephFlow instance with the Kafka sink added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )

        # Convert properties dict to Java Map
        java_properties = None
        if properties:
            java_properties = ZephFlow._gateway.jvm.java.util.HashMap()
            for k, v in properties.items():
                java_properties.put(k, v)

        new_java_flow = self._java_flow.kafkaSink(
            broker, topic, partition_key_field_expr, java_encoding_type, java_properties
        )
        return ZephFlow(new_java_flow)

    def stdout_sink(self, encoding_type: str):
        """
        Add a standard output sink to the flow.

        Args:
            encoding_type: Encoding type for the output (e.g., "JSON_OBJECT")

        Returns:
            ZephFlow: A new ZephFlow instance with the stdout sink added
        """
        if ZephFlow._jvm is None:
            raise RuntimeError("Gateway is not initialized.")
        java_encoding_type = ZephFlow._jvm.io.fleak.zephflow.lib.serdes.EncodingType.valueOf(
            encoding_type
        )
        new_java_flow = self._java_flow.stdoutSink(java_encoding_type)
        return ZephFlow(new_java_flow)

    def append_node(self, command_name: str, config_str: str):
        """
        Add a custom node to the flow.

        Args:
            command_name: Name of the command
            config_str: Configuration string for the command

        Returns:
            ZephFlow: A new ZephFlow instance with the node added
        """
        new_java_flow = self._java_flow.appendNode(command_name, config_str)
        return ZephFlow(new_java_flow)

    def build_dag(self):
        """
        Build the directed acyclic graph (DAG) for this flow.

        Returns:
            Object: Java AdjacencyListDagDefinition object
        """
        return self._java_flow.buildDag()

    def execute(self, job_id: str, env: str, service: str):
        """
        Execute the flow with the given job details.

        Args:
            job_id: Unique identifier for the job
            env: Environment name
            service: Service name
        """
        self._java_flow.execute(job_id, env, service)

    def submit_api_endpoint(self, http_starter_host_url: str):
        """
        Submit the flow to an API endpoint.

        Args:
            http_starter_host_url: URL of the HTTP starter host

        Returns:
            str: Response from the API endpoint
        """
        return self._java_flow.submitApiEndpoint(http_starter_host_url)

    def process(
        self,
        events,
        calling_user="default_user",
        include_error_by_step=True,
        include_output_by_step=True,
    ):
        """
        Process a list of events through the flow.

        Args:
            events: List of event dictionaries to process
            calling_user: User ID for the process call
            include_output_by_step: Whether to include output by step in the result
            include_error_by_step: Whether to include errors by step in the result

        Returns:
            Object: Result of the processing
        """
        # Convert Python list to Java List of RecordFleakData
        java_events = self._convert_event_list(events)

        # Create the DagRunConfig
        NoSourceDagRunner = ZephFlow._jvm.io.fleak.zephflow.runner.NoSourceDagRunner

        run_config = NoSourceDagRunner.DagRunConfig(include_error_by_step, include_output_by_step)

        # Call Java process method
        java_dag_result = self._java_flow.process(java_events, calling_user, run_config)
        return convert_result_to_python(java_dag_result)

    def _convert_event_list(self, events):
        """Convert Python list to Java List."""
        java_list = ZephFlow._gateway.jvm.java.util.ArrayList()

        for event in events:
            java_event = self._dict_to_fleak_data(event)
            java_list.add(java_event)

        return java_list

    def _dict_to_fleak_data(self, data):
        """Convert Python dict to Java FleakData."""
        # Convert Python dict to Java Map
        java_map = ZephFlow._gateway.jvm.java.util.HashMap()

        for key, value in data.items():
            java_value = self._python_to_java(value)
            java_map.put(key, java_value)

        # Use FleakData.wrap
        return ZephFlow._jvm.io.fleak.zephflow.api.structure.FleakData.wrap(java_map)

    def _python_to_java(self, value):
        """Convert Python values to Java equivalents."""
        if isinstance(value, dict):
            java_map = ZephFlow._gateway.jvm.java.util.HashMap()
            for k, v in value.items():
                java_map.put(k, self._python_to_java(v))
            return java_map
        elif isinstance(value, list):
            java_list = ZephFlow._gateway.jvm.java.util.ArrayList()
            for item in value:
                java_list.add(self._python_to_java(item))
            return java_list
        elif value is None:
            return None
        else:
            # Primitives
            return value


# Convenience function at module level
def start_flow():
    """
    Convenience function to start a new ZephFlow.

    Example:
        >>> import zephflow
        >>> flow = zephflow.start_flow()
    """
    return ZephFlow.start_flow()
