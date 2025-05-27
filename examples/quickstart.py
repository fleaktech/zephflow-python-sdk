#!/usr/bin/env python3
"""
ZephFlow Python SDK Quick Start Example

This example demonstrates basic usage of the ZephFlow Python SDK.
"""

import zephflow


def simple_filter_example():
  """Example: Simple filtering and processing."""
  print("=== Simple Filter Example ===")

  # Create a flow that filters events
  flow = (
    zephflow.ZephFlow.start_flow()
    .filter("$.value > 10")
    .stdout_sink("JSON_OBJECT")
  )

  # Process some test events
  events = [
    {"id": 1, "value": 5, "name": "below_threshold"},
    {"id": 2, "value": 15, "name": "above_threshold"},
    {"id": 3, "value": 25, "name": "well_above_threshold"}
  ]

  print("Processing events...")
  result = flow.process(events)
  print(f"\nProduced {result.getOutputEvents().size()} total records")


def transformation_example():
  """Example: Data transformation with eval."""
  print("\n=== Transformation Example ===")

  # Create a flow that transforms data
  flow = (
    zephflow.ZephFlow.start_flow()
    .eval("""
            dict(
                id=$.id,
                original_value=$.value,
                doubled_value=$.value * 2,
                category=case(
                    $.value < 10 => 'low',
                    $.value < 20 => 'medium',
                    _ => 'high'
                )
            )
        """)
    .stdout_sink("JSON_OBJECT")
  )

  # Process events
  events = [
    {"id": 1, "value": 5},
    {"id": 2, "value": 15},
    {"id": 3, "value": 25}
  ]

  print("Transforming events...")
  result = flow.process(events)
  print(f"\nProduced {result.getOutputEvents().size()} records")


def merge_flows_example():
  """Example: Merging multiple flows."""
  print("\n=== Merge Flows Example ===")

  # Create two separate flows with different filters
  high_value_flow = (
    zephflow.ZephFlow.start_flow()
    .filter("$.value >= 20")
  )

  priority_flow = (
    zephflow.ZephFlow.start_flow()
    .filter("$.priority == 'high'")
  )

  # Merge the flows and add common processing
  merged_flow = (
    zephflow.ZephFlow.merge(high_value_flow, priority_flow)
    .eval("dict(id=$.id, reason='Selected for processing')")
    .stdout_sink("JSON_OBJECT")
  )

  # Process events - some will match one filter, some the other
  events = [
    {"id": 1, "value": 25, "priority": "low"},  # Matches high_value_flow
    {"id": 2, "value": 5, "priority": "high"},  # Matches priority_flow
    {"id": 3, "value": 10, "priority": "medium"},  # Matches neither
    {"id": 4, "value": 30, "priority": "high"}  # Matches both
  ]

  print("Processing with merged flows...")
  # Note: In the actual merge, duplicate events (matching both filters)
  # may appear twice unless deduplicated
  result = merged_flow.process(events)
  print(f"\nProcessed {result.getOutputEvents().size()} records")


def error_handling_example():
  """Example: Handling errors with assertions."""
  print("\n=== Error Handling Example ===")

  # Create a flow with an assertion
  flow = (
    zephflow.ZephFlow.start_flow()
    .assertion("$.required_field != null")
    .eval("dict(id=$.id, processed_value=$.required_field * 2)")
    .stdout_sink("JSON_OBJECT")
  )

  # Process events - some will fail the assertion
  events = [
    {"id": 1, "required_field": 10},
    {"id": 2, "required_field": None},  # This will fail
    {"id": 3, "required_field": 20}
  ]

  print("Processing with assertions...")
  result = flow.process(events, include_error_by_step=True)
  print(f"\nTotal: {result.getOutputEvents().size()}")

  # Check failures
  if result.getErrorByStep().size() > 0:
    print(f"\nFailed events: {errors_by_step_str(result.getErrorByStep())}")


def errors_by_step_str(error_by_step) -> str:
  str_parts = []
  for step, err_by_src in error_by_step.items():
    str_parts.append(f"{step} -> \n{errors_by_source_str(err_by_src)}")
  return "".join(str_parts)


def errors_by_source_str(error_by_source) -> str:
  str_parts = []
  for source, errors in error_by_source.items():
    str_parts.append("\t")
    str_parts.append(f"{source}->{errors_str(errors)}")
    str_parts.append("\n")
  return "".join(str_parts)


def errors_str(errors):
  str_parts = []
  for e in errors:
    str_parts.append(f"(error_event: {e.inputEvent().unwrap().toString()}, error_message: {e.errorMessage()})")
  return "[" + ",".join(str_parts) + "]"


def main():
  """Run all examples."""
  print("ZephFlow Python SDK Examples")
  print("===========================\n")

  try:
    simple_filter_example()
    transformation_example()
    merge_flows_example()
    error_handling_example()

    print("\n✅ All examples completed successfully!")

  except Exception as e:
    print(f"\n❌ Error running examples: {e}")
    print("\nMake sure:")
    print("- Java 21 is installed")
    print("- You have internet connection (for JAR download)")
    print("- Or set ZEPHFLOW_MAIN_JAR environment variable")


if __name__ == "__main__":
  main()
