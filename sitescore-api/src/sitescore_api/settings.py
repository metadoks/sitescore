from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    broker_url: str
    api_key_pepper: str
    analysis_deadline_seconds: int = 900
    poll_retry_after_seconds: int = 3
    worker_soft_time_limit_seconds: int = 840
    worker_hard_time_limit_seconds: int = 900

    def __post_init__(self) -> None:
        for name in ("database_url", "broker_url", "api_key_pepper"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be configured")
        if not self.database_url.startswith(("postgresql+psycopg://", "postgresql://")):
            raise ValueError("database_url must use PostgreSQL")
        if not self.broker_url.startswith("redis://"):
            raise ValueError("broker_url must use Redis")
        if len(self.api_key_pepper.encode("utf-8")) < 32:
            raise ValueError("api_key_pepper must contain at least 32 UTF-8 bytes")
        for name in (
            "analysis_deadline_seconds",
            "poll_retry_after_seconds",
            "worker_soft_time_limit_seconds",
            "worker_hard_time_limit_seconds",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if self.worker_soft_time_limit_seconds >= self.worker_hard_time_limit_seconds:
            raise ValueError("worker soft time limit must be below hard time limit")
        if self.worker_hard_time_limit_seconds > self.analysis_deadline_seconds:
            raise ValueError("worker hard time limit must not exceed durable analysis deadline")

    @classmethod
    def from_env(cls) -> "Settings":
        missing = [
            name
            for name in ("SITESCORE_DATABASE_URL", "SITESCORE_BROKER_URL", "SITESCORE_API_KEY_PEPPER")
            if not os.getenv(name)
        ]
        if missing:
            raise ValueError("missing required production configuration")
        return cls(
            database_url=os.environ["SITESCORE_DATABASE_URL"],
            broker_url=os.environ["SITESCORE_BROKER_URL"],
            api_key_pepper=os.environ["SITESCORE_API_KEY_PEPPER"],
            analysis_deadline_seconds=int(os.getenv("SITESCORE_ANALYSIS_DEADLINE_SECONDS", "900")),
            poll_retry_after_seconds=int(os.getenv("SITESCORE_POLL_RETRY_AFTER_SECONDS", "3")),
            worker_soft_time_limit_seconds=int(os.getenv("SITESCORE_WORKER_SOFT_LIMIT_SECONDS", "840")),
            worker_hard_time_limit_seconds=int(os.getenv("SITESCORE_WORKER_HARD_LIMIT_SECONDS", "900")),
        )
