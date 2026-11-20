"""Game rules and JSON history storage."""
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CASE_FILE = BASE_DIR / "data" / "demo_cases.json"
HISTORY_FILE = BASE_DIR / "data" / "history.json"


def load_demo_cases():
    with CASE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def choose_demo_case():
    return random.choice(load_demo_cases())


def public_case(case, discovered_ids):
    """Return a safe copy with undiscovered clue details hidden."""
    result = {k: v for k, v in case.items()
              if k not in ("culprit_id", "solution", "hints")}
    result["evidence"] = []
    for item in case["evidence"]:
        clue = {"id": item["id"], "name": item["name"],
                "description": item["description"],
                "discovered": item["id"] in discovered_ids}
        if clue["discovered"]:
            clue["detail"] = item["detail"]
        result["evidence"].append(clue)
    return result


def read_history():
    try:
        if HISTORY_FILE.exists():
            with HISTORY_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_result(result):
    """Append one completed case. Keep the most recent 100 records."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history = read_history()
    history.insert(0, result)
    with HISTORY_FILE.open("w", encoding="utf-8") as file:
        json.dump(history[:100], file, indent=2)


def progress(game):
    total = len(game["case"]["evidence"]) + len(game["case"]["puzzles"])
    done = len(game["discovered"]) + len(game["completed_puzzles"])
    return min(100, int(done / total * 100)) if total else 0
