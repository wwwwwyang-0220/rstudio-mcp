from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 6312
    allowed_dirs: list[Path] = field(default_factory=list)
    execution_enabled: bool = False

    def is_path_allowed(self, path: Path) -> bool:
        """Return True if path resolves to within any authorized directory."""
        resolved = Path(path).resolve()
        return any(
            resolved.is_relative_to(Path(d).resolve())
            for d in self.allowed_dirs
        )
