import json
from pathlib import Path


class Storage:
    """Handles saving and loading of recorded actions as JSON."""

    @staticmethod
    def save(path, actions):
        """Save actions to JSON file (overwrites existing, ensures dirs)."""
        path = Path(path)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(actions or [], f, indent=2, ensure_ascii=False)
            print(f"[INFO] Saved: {path}")
        except Exception as e:
            print(f"[STORAGE ERROR] Failed to save {path}: {e}")

    @staticmethod
    def load(path):
        """Load actions from JSON file or return empty list on failure."""
        path = Path(path)
        if not path.exists():
            print(f"[WARN] File not found: {path}")
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[STORAGE ERROR] Failed to load {path}: {e}")
            return []
