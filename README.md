# ZephFlow Python SDK

[![PyPI version](https://img.shields.io/pypi/v/zephflow.svg)](https://pypi.org/project/zephflow/)
[![Python Versions](https://img.shields.io/pypi/pyversions/zephflow.svg)](https://pypi.org/project/zephflow/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Python SDK for building and running ZephFlow data processing pipelines. ZephFlow provides a powerful, intuitive API for stream processing, data transformation, and event-driven architectures.

## Features

- **Simple, fluent API** for building data processing pipelines
- **Powerful filtering** using JSONPath expressions
- **Data transformation** with the eval expression language
- **Flow composition** - merge and combine multiple flows
- **Error handling** with assertions and error tracking
- **Multiple sink options** for outputting processed data
- **Java-based engine** for high performance processing

## Documentation

For comprehensive documentation, tutorials, and API reference, visit: [https://docs.fleak.ai/zephflow](https://docs.fleak.ai/zephflow)

## Prerequisites

- Python 3.8 or higher
- Java 17 or higher (required for the processing engine)

## Installation

Install ZephFlow using pip:

```bash
pip install zephflow
```

## Quick Start

Here's a simple example to get you started with ZephFlow:

```python
import zephflow

# Create a flow that filters and transforms events
flow = (
    zephflow.ZephFlow.start_flow()
    .filter("$.value > 10")  # Keep only events with value > 10
    .eval("""
        dict(
            id=$.id,
            doubled_value=$.value * 2,
            category=case(
                $.value < 20 => 'medium',
                _ => 'high'
            )
        )
    """)
)

# Process some events
events = [
    {"id": 1, "value": 5},   # Will be filtered out
    {"id": 2, "value": 15},  # Will be processed
    {"id": 3, "value": 25}   # Will be processed
]

result = flow.process(events)
print(f"Processed {result.getOutputEvents().size()} events")
```

If you already have a workflow file:

```python
import zephflow

zephflow.ZephFlow.execute_dag("my_dag.yaml")
```

## Troubleshooting
### macOS SSL Certificate Issue
If you're on macOS and encounter an error like:

```<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1007)>
This indicates that Python cannot verify SSL certificates due to missing system root certificates.
```

#### Solution
Run the certificate installation script that comes with your Python installation:

```
/Applications/Python\ 3.x/Install\ Certificates.command
Replace 3.x with your installed version (e.g., 3.10). This installs the necessary certificates so Python can verify HTTPS downloads.
```

## Core Concepts

### Filtering

Use JSONPath expressions to filter events:

```python
flow = (
    zephflow.ZephFlow.start_flow()
    .filter("$.priority == 'high' && $.value >= 100")
)
```

### Transformation

Transform data using the eval expression language:

```python
flow = (
    zephflow.ZephFlow.start_flow()
    .eval("""
        dict(
            timestamp=now(),
            original_id=$.id,
            processed_value=$.value * 1.1,
            status='processed'
        )
    """)
)
```

### Merging Flows

Combine multiple flows for complex processing logic:

```python
high_priority = zephflow.ZephFlow.start_flow().filter("$.priority == 'high'")
large_value = zephflow.ZephFlow.start_flow().filter("$.value >= 1000")

merged = zephflow.ZephFlow.merge(high_priority, large_value)
```

### Error Handling

Add assertions to validate data and handle errors:

```python
flow = (
  zephflow.ZephFlow.start_flow()
  .assertion("$.required_field != null")
  .assertion("$.value >= 0")
  .eval("dict(id=$.id, validated_value=$.value)")
)

result = flow.process(events, include_error_by_step=True)
if result.getErrorByStep().size() > 0:
  print("Some events failed validation")
```

## S3 Dead Letter Queue (DLQ)

ZephFlow supports automatic error handling by storing failed events to Amazon S3 using a Dead Letter Queue mechanism. **S3 DLQ works with data sources** (like file_source, kafka_source, etc.) and captures events that fail during **data ingestion, conversion, or pipeline processing** (including filter, assertion, eval failures).

### S3 DLQ Configuration with File Source

Configure S3 DLQ to automatically capture events that fail during data source processing:

```python
import tempfile
import json
import zephflow
from zephflow import JobContext, S3DlqConfig

# Create test data file with some invalid data
test_data = [
    {"user_id": 1, "value": 100, "category": "A"},
    {"user_id": 2, "value": 200, "category": "B"},
    "invalid_json_string",  # This will cause parsing failure -> DLQ
    {"malformed": "json", "missing": 0 },  # This will cause parsing failure -> DLQ
]

# Write test data to file (including invalid JSON)
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    for item in test_data:
        if isinstance(item, dict):
            f.write(json.dumps(item) + '\n')
        else:
            f.write(str(item) + '\n')  # Write invalid JSON
    input_file = f.name

# Configure S3 DLQ
dlq_config = S3DlqConfig(
    region="us-west-2",
    bucket="error-events-bucket",
    batch_size=100,                    # Events to batch before writing
    flush_interval_millis=30000,       # Max wait time (30 seconds)
    access_key_id="your-access-key",
    secret_access_key="your-secret-key"
)

# Create JobContext with DLQ configuration
job_context = (
    JobContext.builder()
    .metric_tags({"env": "production", "service": "data-processor"})
    .dlq_config(dlq_config)
    .build()
)

# Create a flow with file source - DLQ will capture parsing failures
flow = (
    zephflow.ZephFlow.start_flow(job_context)
    .file_source(input_file, "JSON_OBJECT")  # Invalid JSON lines will go to DLQ
    .filter("$.value > 0")                   # Normal pipeline processing
    .eval("""
        dict(
            user_id=$.user_id,
            processed_value=$.value * 1.1,
            processed_at=now()
        )
    """)
    .stdout_sink("JSON_OBJECT")
)

# Execute the flow - source parsing failures will be sent to S3 DLQ
flow.execute("data-processor", "production", "json-processor")
print(f"Invalid JSON events sent to S3 DLQ: error-events-bucket")

# Cleanup
import os
os.unlink(input_file)
```

### S3 DLQ with Kafka Source

S3 DLQ also works with streaming sources like Kafka to capture deserialization failures:

```python
import zephflow
from zephflow import JobContext, S3DlqConfig

# Configure S3 DLQ for Kafka processing errors
dlq_config = S3DlqConfig(
    region="us-east-1",
    bucket="kafka-processing-errors",
    batch_size=50,
    flush_interval_millis=10000,
    access_key_id="your-access-key",
    secret_access_key="your-secret-key"
)

job_context = (
    JobContext.builder()
    .dlq_config(dlq_config)
    .metric_tags({"env": "production", "service": "kafka-processor"})
    .build()
)

# Kafka source with DLQ - will capture messages that fail JSON parsing
flow = (
    zephflow.ZephFlow.start_flow(job_context)
    .kafka_source(
        broker="localhost:9092",
        topic="user-events",
        group_id="processor-group",
        encoding_type="JSON_OBJECT"  # Invalid JSON messages will go to DLQ
    )
    .filter("$.event_type == 'purchase'")
    .eval("""
        dict(
            user_id=$.user_id,
            amount=$.amount,
            processed_at=now()
        )
    """)
    .stdout_sink("JSON_OBJECT")
)

# This would run continuously, capturing Kafka deserialization failures to S3 DLQ
# flow.execute("kafka-processor", "production", "purchase-events")
```

### S3 DLQ with Pipeline Processing Failures

S3 DLQ also captures pipeline processing failures like assertion errors:

```python
import tempfile
import json
import zephflow
from zephflow import JobContext, S3DlqConfig

# Create test data with values that will cause assertion failures
test_data = [
    {"user_id": 1, "value": 100, "category": "A"},  # Will pass
    {"user_id": 2, "value": 1500, "category": "B"}, # Will fail assertion (> 1000) -> DLQ
    {"user_id": 3, "value": 50, "category": "A"},   # Will pass
    {"user_id": 4, "value": 2000, "category": "C"}, # Will fail assertion (> 1000) -> DLQ
]

# Write test data to file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    for item in test_data:
        f.write(json.dumps(item) + '\n')
    input_file = f.name

# Configure S3 DLQ
dlq_config = S3DlqConfig(
    region="us-west-2",
    bucket="pipeline-error-events",
    batch_size=10,
    flush_interval_millis=5000,
    access_key_id="your-access-key",
    secret_access_key="your-secret-key"
)

job_context = (
    JobContext.builder()
    .metric_tags({"env": "production", "service": "data-validator"})
    .dlq_config(dlq_config)
    .build()
)

# Pipeline with assertion that will cause some events to fail
flow = (
    zephflow.ZephFlow.start_flow(job_context)
    .file_source(input_file, "JSON_OBJECT")
    .filter("$.value > 0")                  # Basic filtering
    .assertion("$.value < 1000")            # This will fail for value=1500,2000 -> DLQ
    .eval("""
        dict(
            user_id=$.user_id,
            validated_value=$.value,
            processed_at=now()
        )
    """)
    .stdout_sink("JSON_OBJECT")
)

# Execute - assertion failures will be sent to S3 DLQ
flow.execute("data-validator", "production", "validation-service")
print(f"Assertion failures sent to S3 DLQ: pipeline-error-events")

# Cleanup
import os
os.unlink(input_file)
```

### S3 DLQ Configuration Options

The `S3DlqConfig` supports the following parameters:

- `region`: AWS region where the DLQ bucket is located
- `bucket`: S3 bucket name for storing failed events
- `batch_size`: Number of events to batch before writing (default: 100)
- `flush_interval_millis`: Maximum time to wait before flushing events (default: 5000ms)
- `access_key_id`: AWS access key (optional, uses default credential chain if not provided)
- `secret_access_key`: AWS secret key (optional, uses default credential chain if not provided)

### DLQ Error Event Format

Failed source events are stored in S3 using Avro format with the following structure:

- **processingTimestamp**: Timestamp when the error occurred (milliseconds)
- **key**: Original message key (bytes, nullable)
- **value**: Original message value (bytes, nullable)
- **metadata**: Additional metadata about the source (map of strings, nullable)
- **errorMessage**: Error details including stack trace (string)

### Common S3 DLQ Use Cases

S3 DLQ captures failures when using **data sources**, including:

- **JSON parsing failures** in file_source or kafka_source
- **Deserialization errors** when converting raw data to structured format
- **Schema validation failures** at the source level
- **Network or I/O errors** during data fetching
- **Pipeline processing failures** like assertion failures, eval errors, or filter exceptions
- **Data transformation errors** in any pipeline step

**Note**: S3 DLQ **only works with data sources** (file_source, kafka_source, etc.). When using `flow.process(events)` with in-memory data, pipeline failures are handled through `result.getErrorByStep()` instead.

## Examples

For more detailed examples, check out [Quick Start Example](https://github.com/fleaktech/zephflow-python-sdk/blob/main/examples/quickstart.py) - Basic filtering and transformation

## Environment Variables

- `ZEPHFLOW_MAIN_JAR` - Path to a custom ZephFlow JAR file (optional)
- `ZEPHFLOW_JAR_DIR` - Directory for storing downloaded JAR files (optional)


## Support

- **Documentation**: [https://docs.fleak.ai/zephflow](https://docs.fleak.ai/zephflow)
- **Discussions**: [Slack](https://join.slack.com/t/fleak-hq/shared_invite/zt-361k9cnhf-9~mmjpOH1IbZfRxeXplfKA)

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## About Fleak

ZephFlow is developed and maintained by [Fleak Tech Inc.](https://fleak.ai), building the future of data processing and streaming analytics.
