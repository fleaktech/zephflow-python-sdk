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
