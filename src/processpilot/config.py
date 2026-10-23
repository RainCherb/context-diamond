"""Centralized configuration. External inference is OPT-IN only."""
from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path


def _float_env(key: str, default: float, *, minimum: float = 0.0) -> float:
    """Read a finite float from the environment and clamp it to a safe minimum."""
    try:
        value = float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return max(value, minimum)


def _path_env(key: str, default: str) -> Path:
    value = os.getenv(key, default).strip()
    return Path(value or default)


def _hosts_env(key: str) -> tuple[str, ...]:
    raw = os.getenv(key, "localhost,127.0.0.1,::1,testserver,processpilot")
    hosts = tuple(item.strip().lower() for item in raw.split(",") if item.strip())
    return hosts or ("localhost", "127.0.0.1", "::1")


@dataclass(frozen=True)
class Settings:
    mode: str = "offline"
    db_path: Path = Path("data/processpilot.sqlite3")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout: float = 15.0
    input_usd_per_million: float = 0.25
    output_usd_per_million: float = 1.0
    allowed_hosts: tuple[str, ...] = ("localhost", "127.0.0.1", "::1", "testserver", "processpilot")

    @classmethod
    def from_env(cls) -> "Settings":
        mode = os.getenv("PILOT_MODE", "offline").lower().strip()
        if mode not in ("offline", "remote"):
            raise ValueError("PILOT_MODE must be offline or remote")
        return cls(
            mode=mode,
            db_path=_path_env("PILOT_DB", "data/processpilot.sqlite3"),
            llm_base_url=os.getenv("PILOT_LLM_BASE_URL", "").strip().rstrip("/"),
            llm_model=os.getenv("PILOT_LLM_MODEL", "").strip(),
            llm_api_key=os.getenv("PILOT_LLM_API_KEY", "").strip(),
            llm_timeout=_float_env("PILOT_LLM_TIMEOUT_SECONDS", 15.0, minimum=0.1),
            input_usd_per_million=_float_env("PILOT_INPUT_USD_PER_1M", 0.25),
            output_usd_per_million=_float_env("PILOT_OUTPUT_USD_PER_1M", 1.0),
            allowed_hosts=_hosts_env("PILOT_ALLOWED_HOSTS"),
        )

    @property
    def remote_ready(self) -> bool:
        return self.mode == "remote" and bool(self.llm_base_url and self.llm_model)
