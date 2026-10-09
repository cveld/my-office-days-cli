from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


def data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / "my-office-days-cli"
    return Path.home() / ".config" / "my-office-days-cli"


@dataclass(slots=True)
class Config:
    base_url: str | None = None
    employee_guid: str | None = None

    @classmethod
    def load(cls) -> "Config":
        path = data_dir() / "config.json"
        if not path.exists():
            return cls()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            base_url=raw.get("base_url"),
            employee_guid=raw.get("employee_guid"),
        )

    def save(self) -> Path:
        directory = data_dir()
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "config.json"
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        return path
