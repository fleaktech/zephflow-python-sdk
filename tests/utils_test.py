import unittest
from unittest.mock import Mock

from zephflow.utils import convert_result_to_python


class TestDagResultConverter(unittest.TestCase):
    """Test cases for convert_result_to_python function"""

    def setUp(self):
        self.sample_dict_data = {"field1": "value1", "field2": 42, "field3": True}

    def test_convert_result_none_input(self):
        """Test that None input raises ValueError"""
        with self.assertRaises(ValueError) as context:
            convert_result_to_python(None)
        self.assertIn("dag_result cannot be None", str(context.exception))

    def test_convert_with_empty_dict(self):
        """Test conversion with empty dict input"""
        result = convert_result_to_python({})

        expected = {
            "output_events": {},
            "output_by_step": {},
            "error_by_step": {},
            "sink_result_map": {},
        }
        self.assertEqual(result, expected)

    def test_convert_with_dict_containing_data(self):
        """Test conversion with dict containing sample data"""
        mock_record = Mock()
        mock_record.unwrap.return_value = self.sample_dict_data

        input_dict = {
            "outputEvents": {"exit1": [mock_record, {"already": "dict"}]},
            "outputByStep": {"step1": {"source1": [mock_record]}},
            "errorByStep": {},
            "sinkResultMap": {},
        }

        result = convert_result_to_python(input_dict)

        self.assertEqual(result["output_events"]["exit1"][0], self.sample_dict_data)
        self.assertEqual(result["output_events"]["exit1"][1], {"already": "dict"})
        self.assertEqual(result["output_by_step"]["step1"]["source1"][0], self.sample_dict_data)

    def test_convert_with_java_object(self):
        """Test conversion with mocked Java DagResult object"""
        mock_record = Mock()
        mock_record.unwrap.return_value = self.sample_dict_data

        mock_list = Mock()
        mock_list.size.return_value = 1
        mock_list.get.return_value = mock_record

        mock_output_events = Mock()
        mock_output_events.keySet.return_value = ["exit1"]  # Return actual list, not Mock
        mock_output_events.get.return_value = mock_list

        mock_step_map = Mock()
        mock_step_map.keySet.return_value = ["source1"]  # Return actual list, not Mock
        mock_step_map.get.return_value = mock_list

        mock_output_by_step = Mock()
        mock_output_by_step.keySet.return_value = ["step1"]  # Return actual list, not Mock
        mock_output_by_step.get.return_value = mock_step_map

        mock_empty_map = Mock()
        mock_empty_map.keySet.return_value = []  # Return actual empty list, not Mock

        mock_dag_result = Mock()
        mock_dag_result.getOutputEvents.return_value = mock_output_events
        mock_dag_result.getOutputByStep.return_value = mock_output_by_step
        mock_dag_result.getErrorByStep.return_value = mock_empty_map
        mock_dag_result.getSinkResultMap.return_value = mock_empty_map

        result = convert_result_to_python(mock_dag_result)

        self.assertEqual(result["output_events"]["exit1"][0], self.sample_dict_data)
        self.assertEqual(result["output_by_step"]["step1"]["source1"][0], self.sample_dict_data)
        self.assertEqual(result["error_by_step"], {})
        self.assertEqual(result["sink_result_map"], {})

    def test_convert_error_output(self):
        """Test ErrorOutput conversion"""
        # Mock input event
        mock_input_event = Mock()
        mock_input_event.unwrap.return_value = {"event": "data"}

        error_dict = {"input_event": {"event": "data"}, "error_message": "Test error"}

        input_dict = {
            "outputEvents": {},
            "outputByStep": {},
            "errorByStep": {"step1": {"source1": [error_dict]}},
            "sinkResultMap": {},
        }

        result = convert_result_to_python(input_dict)

        self.assertEqual(result["error_by_step"]["step1"]["source1"][0], error_dict)

    def test_convert_error_output_java_object(self):
        """Test ErrorOutput conversion from Java object"""
        mock_input_event = Mock()
        mock_input_event.unwrap.return_value = {"event": "data"}

        mock_error = Mock()
        mock_error.inputEvent.return_value = mock_input_event
        mock_error.errorMessage.return_value = "Java error"

        mock_errors_list = Mock()
        mock_errors_list.size.return_value = 1
        mock_errors_list.get.return_value = mock_error

        mock_source_map = Mock()
        mock_source_map.keySet.return_value = ["source1"]  # Actual list, not Mock
        mock_source_map.get.return_value = mock_errors_list

        mock_error_by_step = Mock()
        mock_error_by_step.keySet.return_value = ["step1"]  # Actual list, not Mock
        mock_error_by_step.get.return_value = mock_source_map

        mock_dag_result = Mock()
        mock_dag_result.getOutputEvents.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getOutputByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getErrorByStep.return_value = mock_error_by_step
        mock_dag_result.getSinkResultMap.return_value = Mock(keySet=Mock(return_value=[]))

        result = convert_result_to_python(mock_dag_result)

        expected_error = {"input_event": {"event": "data"}, "error_message": "Java error"}
        self.assertEqual(result["error_by_step"]["step1"]["source1"][0], expected_error)

    def test_convert_sink_result(self):
        """Test SinkResult conversion"""
        mock_input_event = Mock()
        mock_input_event.unwrap.return_value = {"failed": "event"}

        mock_failure = Mock()
        mock_failure.inputEvent.return_value = mock_input_event
        mock_failure.errorMessage.return_value = "Sink failure"

        sink_result_dict = {
            "input_count": 10,
            "success_count": 8,
            "failure_events": [
                {"input_event": {"failed": "event"}, "error_message": "Sink failure"}
            ],
            "error_count": 2,
        }

        input_dict = {
            "outputEvents": {},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {"sink1": sink_result_dict},
        }

        result = convert_result_to_python(input_dict)

        self.assertEqual(result["sink_result_map"]["sink1"], sink_result_dict)

    def test_convert_sink_result_java_object(self):
        """Test SinkResult conversion from Java object"""
        mock_input_event = Mock()
        mock_input_event.unwrap.return_value = {"failed": "event"}

        mock_failure = Mock()
        mock_failure.inputEvent.return_value = mock_input_event
        mock_failure.errorMessage.return_value = "Java sink failure"

        mock_failures_list = Mock()
        mock_failures_list.size.return_value = 1
        mock_failures_list.get.return_value = mock_failure

        mock_sink_result = Mock()
        mock_sink_result.getInputCount.return_value = 15
        mock_sink_result.getSuccessCount.return_value = 12
        mock_sink_result.getFailureEvents.return_value = mock_failures_list
        mock_sink_result.errorCount.return_value = 3

        mock_sink_map = Mock()
        mock_sink_map.keySet.return_value = ["sink1"]  # Actual list, not Mock
        mock_sink_map.get.return_value = mock_sink_result

        mock_dag_result = Mock()
        mock_dag_result.getOutputEvents.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getOutputByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getErrorByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getSinkResultMap.return_value = mock_sink_map

        result = convert_result_to_python(mock_dag_result)

        expected_sink = {
            "input_count": 15,
            "success_count": 12,
            "failure_events": [
                {"input_event": {"failed": "event"}, "error_message": "Java sink failure"}
            ],
            "error_count": 3,
        }
        self.assertEqual(result["sink_result_map"]["sink1"], expected_sink)

    def test_invalid_java_object(self):
        """Test that invalid Java object raises ValueError"""
        # Create a mock with a limited spec to prevent automatic method creation
        mock_invalid_object = Mock(spec=[])  # Empty spec means no methods available

        with self.assertRaises(ValueError) as context:
            convert_result_to_python(mock_invalid_object)
        self.assertIn("Expected DagResult object but missing method", str(context.exception))

    def test_java_object_method_call_failure(self):
        """Test handling when Java object methods fail during conversion"""
        # Create a mock that has the required methods but they fail when called
        mock_dag_result = Mock()
        # First make sure validation passes by providing the required methods
        mock_dag_result.getOutputEvents.side_effect = Exception("Java method call failed")
        mock_dag_result.getOutputByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getErrorByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getSinkResultMap.return_value = Mock(keySet=Mock(return_value=[]))

        # This should raise RuntimeError (conversion failure), not ValueError (validation failure)
        with self.assertRaises(RuntimeError) as context:
            convert_result_to_python(mock_dag_result)
        self.assertIn("Failed to convert DagResult to Python", str(context.exception))

    def test_dict_conversion_failure(self):
        """Test handling of conversion failures when input is a dict"""
        mock_record = Mock()
        mock_record.unwrap.side_effect = Exception("Dict conversion failed")

        input_dict = {
            "outputEvents": {"exit1": [mock_record]},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {},
        }

        # This should raise RuntimeError (conversion failure), not ValueError (validation failure)
        with self.assertRaises(RuntimeError) as context:
            convert_result_to_python(input_dict)
        self.assertIn("Failed to convert DagResult to Python", str(context.exception))

    def test_mock_iteration_pattern(self):
        """Test that demonstrates proper Mock configuration for Java collections"""
        mock_map = Mock()
        mock_map.keySet.return_value = ["key1", "key2"]  # Actual list is iterable
        mock_map.get.return_value = Mock(size=Mock(return_value=0))

        mock_dag_result = Mock()
        mock_dag_result.getOutputEvents.return_value = mock_map
        mock_dag_result.getOutputByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getErrorByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getSinkResultMap.return_value = Mock(keySet=Mock(return_value=[]))

        # This should not raise an iteration error
        result = convert_result_to_python(mock_dag_result)

        # Verify the keys were processed
        self.assertIn("key1", result["output_events"])
        self.assertIn("key2", result["output_events"])
        """Test that demonstrates proper Mock configuration for Java collections"""
        # This test shows the correct way to mock Java Map.keySet() to return iterables

        mock_map = Mock()
        mock_map.keySet.return_value = ["key1", "key2"]  # Actual list is iterable
        mock_map.get.return_value = Mock(size=Mock(return_value=0))

        mock_dag_result = Mock()
        mock_dag_result.getOutputEvents.return_value = mock_map
        mock_dag_result.getOutputByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getErrorByStep.return_value = Mock(keySet=Mock(return_value=[]))
        mock_dag_result.getSinkResultMap.return_value = Mock(keySet=Mock(return_value=[]))

        # This should not raise an iteration error
        result = convert_result_to_python(mock_dag_result)

        # Verify the keys were processed
        self.assertIn("key1", result["output_events"])
        self.assertIn("key2", result["output_events"])

    def test_record_unwrap_failure(self):
        """Test handling of RecordFleakData unwrap failure"""
        mock_record = Mock()
        mock_record.unwrap.side_effect = Exception("Unwrap failed")

        input_dict = {
            "outputEvents": {"exit1": [mock_record]},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {},
        }

        with self.assertRaises(RuntimeError) as context:
            convert_result_to_python(input_dict)
        self.assertIn("Failed to unwrap RecordFleakData", str(context.exception))

    def test_error_output_conversion_failure(self):
        """Test handling of ErrorOutput conversion failure"""
        mock_error = Mock()
        mock_error.inputEvent.side_effect = Exception("Input event failed")

        input_dict = {
            "outputEvents": {},
            "outputByStep": {},
            "errorByStep": {"step1": {"source1": [mock_error]}},
            "sinkResultMap": {},
        }

        with self.assertRaises(RuntimeError) as context:
            convert_result_to_python(input_dict)
        self.assertIn("Failed to convert ErrorOutput", str(context.exception))

    def test_sink_result_conversion_failure(self):
        """Test handling of SinkResult conversion failure"""
        mock_sink_result = Mock()
        mock_sink_result.getInputCount.side_effect = Exception("Input count failed")

        input_dict = {
            "outputEvents": {},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {"sink1": mock_sink_result},
        }

        with self.assertRaises(RuntimeError) as context:
            convert_result_to_python(input_dict)
        self.assertIn("Failed to convert SinkResult", str(context.exception))

    def test_none_values_handling(self):
        """Test handling of None values in various places"""
        input_dict = {
            "outputEvents": {"exit1": [None, {"valid": "data"}]},
            "outputByStep": {},
            "errorByStep": {"step1": {"source1": [None]}},
            "sinkResultMap": {"sink1": None},
        }

        result = convert_result_to_python(input_dict)

        self.assertIsNone(result["output_events"]["exit1"][0])
        self.assertEqual(result["output_events"]["exit1"][1], {"valid": "data"})
        self.assertIsNone(result["error_by_step"]["step1"]["source1"][0])
        self.assertIsNone(result["sink_result_map"]["sink1"])


class TestComplexScenarios(unittest.TestCase):
    """Test complex scenarios and edge cases"""

    def test_deeply_nested_structure(self):
        """Test conversion of deeply nested structure"""
        mock_record1 = Mock()
        mock_record1.unwrap.return_value = {"step": "1", "data": "first"}

        mock_record2 = Mock()
        mock_record2.unwrap.return_value = {"step": "2", "data": "second"}

        input_dict = {
            "outputEvents": {"exit1": [mock_record1], "exit2": [mock_record2]},
            "outputByStep": {
                "step1": {"source1": [mock_record1], "source2": [mock_record2]},
                "step2": {"source1": [mock_record1, mock_record2]},
            },
            "errorByStep": {},
            "sinkResultMap": {},
        }

        result = convert_result_to_python(input_dict)

        # Verify nested structure is preserved
        self.assertEqual(len(result["output_events"]), 2)
        self.assertEqual(len(result["output_by_step"]), 2)
        self.assertEqual(len(result["output_by_step"]["step1"]), 2)
        self.assertEqual(len(result["output_by_step"]["step2"]["source1"]), 2)

    def test_mixed_dict_and_java_objects(self):
        """Test conversion with mixed dict and Java objects"""
        # Mix of already converted dicts and Java objects
        mock_java_record = Mock()
        mock_java_record.unwrap.return_value = {"from": "java"}

        dict_record = {"from": "dict"}

        input_dict = {
            "outputEvents": {"mixed": [mock_java_record, dict_record]},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {},
        }

        result = convert_result_to_python(input_dict)

        self.assertEqual(result["output_events"]["mixed"][0], {"from": "java"})
        self.assertEqual(result["output_events"]["mixed"][1], {"from": "dict"})

    def test_large_dataset_simulation(self):
        """Test with simulated large dataset"""
        # Create many mock records
        records = []
        for i in range(100):
            mock_record = Mock()
            mock_record.unwrap.return_value = {"id": i, "value": f"data_{i}"}
            records.append(mock_record)

        input_dict = {
            "outputEvents": {"bulk_exit": records},
            "outputByStep": {},
            "errorByStep": {},
            "sinkResultMap": {},
        }

        result = convert_result_to_python(input_dict)

        # Verify all records were converted
        self.assertEqual(len(result["output_events"]["bulk_exit"]), 100)
        self.assertEqual(result["output_events"]["bulk_exit"][0]["id"], 0)
        self.assertEqual(result["output_events"]["bulk_exit"][99]["id"], 99)
