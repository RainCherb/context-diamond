"""Centralized configuration. External inference is OPT-IN only."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _float_env(key: str, default: float) -> float:
    try:
        return max(float(os.getenv(key, str(default))), 0.0)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    mode: str = "offline"
    db_path: Path = Path("data/processpilot.sqlite3")
    llm_base_url: str = ""
    llm_model: str = ""
    llm_api_key: str = ""
    llm_timeout: float = 15.0
    input_usd_per_million: float = 0.25  # Illustrative default, not live pricing.
    output_usd_per_million: float = 1.0

    @classmethod
    def from_env(cls) -> Settings:
        mode = os.getenv("PILOT_MODE", "offline").lower().strip()
        if mode not in ("offline", "remote"):
            raise ValueError("PILOT_MODE must be offline or remote")
        return cls(
            mode=mode,
            db_path=Path(os.getenv("PILOT_DB", "data/processpilot.sqlite3")),
            llm_base_url=os.getenv("PILOT_LLM_BASE_URL", "").rstrip("/"),
            llm_model=os.getenv("PILOT_LLM_MODEL", ""),
            llm_api_key=os.getenv("PILOT_LLM_API_KEY", ""),
            llm_timeout=_float_env("PILOT_LLM_TIMEOUT_SECONDS", 15.0),
            input_usd_per_million=_float_env("PILOT_INPUT_USD_PER_1M", 0.25),
            output_usd_per_million=_float_env("PILOT_OUTPUT_USD_PER_1M", 1.0),
        )

    @property
    def remote_ready(self) -> bool:
        return self.mode == "remote" and bool(self.llm_base_url and self.llm_model)
