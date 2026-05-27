import json
from pathlib import Path
from threading import Lock


class MemoryStore:
    def __init__(self, file_path: str = "memory_store.json") -> None:
        self._lock = Lock()
        base_path = Path(file_path)
        if not base_path.is_absolute():
            base_path = Path(__file__).parent / base_path
        self.path = base_path
        self.data = {
            "user_name": None,
            "home_location": None,
            "birthday": None,
            "favorite_color": None,
        }
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                self.data.update(raw)
        except Exception:
            pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def set_fact(self, key: str, value: str) -> None:
        clean_key = key.strip().lower()
        clean_value = value.strip()
        if not clean_key or not clean_value:
            return
        with self._lock:
            self.data[clean_key] = clean_value
            self._save()

    def get_fact(self, key: str) -> str | None:
        with self._lock:
            return self.data.get(key)

    def set_user_name(self, name: str) -> None:
        clean_name = name.strip().title()
        if not clean_name:
            return
        self.set_fact("user_name", clean_name)

    def get_user_name(self) -> str | None:
        return self.get_fact("user_name")

    def set_home_location(self, location: str) -> None:
        clean_location = location.strip()
        if not clean_location:
            return
        self.set_fact("home_location", clean_location)

    def get_home_location(self) -> str | None:
        return self.get_fact("home_location")
