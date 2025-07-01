import json


def read_file(file) -> str:
    with open(file, "r") as f:
        return f.read()


def is_json(data) -> bool:
    try:
        text = str(data).strip()
        if not (text.startswith("{") or text.startswith("[")):
            return False
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def convert_result_to_python(dag_result):
    """Convert DagResult to Python, handling both Java objects and dicts"""

    if dag_result is None:
        raise ValueError("dag_result cannot be None")

    def convert_record_fleak_data(record):
        """Convert a RecordFleakData Java object to Python dict"""
        if record is None:
            return None
        # If it's already a dict, return it
        if isinstance(record, dict):
            return record
        # Otherwise it's a Java object, call unwrap()
        try:
            return dict(record.unwrap())
        except Exception as e:
            raise RuntimeError(f"Failed to unwrap RecordFleakData: {e}")

    def convert_error_output(error):
        """Convert an ErrorOutput Java object to Python dict"""
        if error is None:
            return None
        # If it's already a dict, return it
        if isinstance(error, dict):
            return error
        # Otherwise it's a Java object
        try:
            return {
                "input_event": dict(error.inputEvent().unwrap()),
                "error_message": str(error.errorMessage()),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to convert ErrorOutput: {e}")

    def convert_sink_result(sink_result):
        """Convert a SinkResult Java object to Python dict"""
        if sink_result is None:
            return None
        # If it's already a dict, return it
        if isinstance(sink_result, dict):
            return sink_result
        # Otherwise it's a Java object
        try:
            failure_events = []
            failure_events_list = sink_result.getFailureEvents()
            for i in range(failure_events_list.size()):
                error = failure_events_list.get(i)
                failure_events.append(convert_error_output(error))

            return {
                "input_count": int(sink_result.getInputCount()),
                "success_count": int(sink_result.getSuccessCount()),
                "failure_events": failure_events,
                "error_count": int(sink_result.errorCount()),  # Include computed field
            }
        except Exception as e:
            raise RuntimeError(f"Failed to convert SinkResult: {e}")

    def convert_events_map(events_map, is_java_object=False):
        """Convert a map of string -> list of RecordFleakData"""
        result = {}
        try:
            if is_java_object:
                for key in events_map.keySet():
                    events_list = events_map.get(key)
                    result[str(key)] = []
                    for i in range(events_list.size()):
                        event = events_list.get(i)
                        result[str(key)].append(convert_record_fleak_data(event))
            else:
                for key, events_list in events_map.items():
                    result[key] = [convert_record_fleak_data(event) for event in events_list]
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to convert events map: {e}")

    def convert_nested_events_map(nested_map, is_java_object=False):
        """Convert a nested map of string -> map -> list of RecordFleakData"""
        result = {}
        try:
            if is_java_object:
                for step_key in nested_map.keySet():
                    step_map = nested_map.get(step_key)
                    result[str(step_key)] = convert_events_map(step_map, is_java_object=True)
            else:
                for step_key, step_map in nested_map.items():
                    result[step_key] = convert_events_map(step_map, is_java_object=False)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to convert nested events map: {e}")

    def convert_nested_errors_map(nested_map, is_java_object=False):
        """Convert a nested map of string -> map -> list of ErrorOutput"""
        result = {}
        try:
            if is_java_object:
                for step_key in nested_map.keySet():
                    step_map = nested_map.get(step_key)
                    result[str(step_key)] = {}
                    for source_key in step_map.keySet():
                        errors_list = step_map.get(source_key)
                        result[str(step_key)][str(source_key)] = []
                        for i in range(errors_list.size()):
                            error = errors_list.get(i)
                            result[str(step_key)][str(source_key)].append(
                                convert_error_output(error)
                            )
            else:
                for step_key, step_map in nested_map.items():
                    result[step_key] = {}
                    for source_key, errors_list in step_map.items():
                        result[step_key][source_key] = [
                            convert_error_output(error) for error in errors_list
                        ]
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to convert nested errors map: {e}")

    def convert_sink_result_map(sink_map, is_java_object=False):
        """Convert a map of string -> SinkResult"""
        result = {}
        try:
            if is_java_object:
                for key in sink_map.keySet():
                    sink_result = sink_map.get(key)
                    result[str(key)] = convert_sink_result(sink_result)
            else:
                for key, sink_result in sink_map.items():
                    result[key] = convert_sink_result(sink_result)
            return result
        except Exception as e:
            raise RuntimeError(f"Failed to convert sink result map: {e}")

    # Main conversion logic
    # Check if dag_result is already a dict
    if isinstance(dag_result, dict):
        # It's already a Python dict, but may contain Java objects inside
        try:
            return {
                "output_events": convert_events_map(dag_result.get("outputEvents", {})),
                "output_by_step": convert_nested_events_map(dag_result.get("outputByStep", {})),
                "error_by_step": convert_nested_errors_map(dag_result.get("errorByStep", {})),
                "sink_result_map": convert_sink_result_map(dag_result.get("sinkResultMap", {})),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to convert DagResult to Python: {e}")
    else:
        # It's a Java object - validate it has the expected methods BEFORE trying conversion
        required_methods = [
            "getOutputEvents",
            "getOutputByStep",
            "getErrorByStep",
            "getSinkResultMap",
        ]
        for method in required_methods:
            if not hasattr(dag_result, method):
                raise ValueError(f"Expected DagResult object but missing method: {method}")

        # Now attempt the conversion
        try:
            return {
                "output_events": convert_events_map(
                    dag_result.getOutputEvents(), is_java_object=True
                ),
                "output_by_step": convert_nested_events_map(
                    dag_result.getOutputByStep(), is_java_object=True
                ),
                "error_by_step": convert_nested_errors_map(
                    dag_result.getErrorByStep(), is_java_object=True
                ),
                "sink_result_map": convert_sink_result_map(
                    dag_result.getSinkResultMap(), is_java_object=True
                ),
            }
        except Exception as e:
            raise RuntimeError(f"Failed to convert DagResult to Python: {e}")
