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
    .stdout_sink("JSON_OBJECT")  # Output to console
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