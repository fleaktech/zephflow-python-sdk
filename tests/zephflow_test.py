from pathlib import Path

from zephflow import ZephFlow


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
