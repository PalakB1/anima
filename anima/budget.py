"""
The Budget — keeps the agent alive without bankrupting its creator.
Tracks token spend, enforces daily limits, and switches between
deep thinking (API) and shallow thinking (local pattern replay).
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict


@dataclass
class UsageRecord:
    date: str
    input_tokens: int = 0
    output_tokens: int = 0
    api_calls: int = 0
    thoughts_generated: int = 0
    thoughts_local: int = 0

    @property
    def estimated_cost_usd(self) -> float:
        # claude-sonnet-4 pricing: $3/M input, $15/M output
        return (self.input_tokens * 3 + self.output_tokens * 15) / 1_000_000


class Budget:
    def __init__(self, path: Path, daily_limit_usd: float = 0.50,
                 max_api_calls_per_day: int = 100):
        self.path = path
        self.daily_limit_usd = daily_limit_usd
        self.max_api_calls_per_day = max_api_calls_per_day
        self._today: UsageRecord | None = None
        self._load()

    def _today_key(self) -> str:
        return time.strftime("%Y-%m-%d")

    def _load(self):
        if self.path.exists():
            data = json.loads(self.path.read_text())
            today_key = self._today_key()
            if today_key in data:
                self._today = UsageRecord(**data[today_key])
            else:
                self._today = UsageRecord(date=today_key)
        else:
            self._today = UsageRecord(date=self._today_key())

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        all_data = {}
        if self.path.exists():
            all_data = json.loads(self.path.read_text())
        all_data[self._today_key()] = asdict(self._today)
        self.path.write_text(json.dumps(all_data, indent=2))

    def can_think_deep(self) -> bool:
        if self._today.date != self._today_key():
            self._today = UsageRecord(date=self._today_key())
        return (
            self._today.estimated_cost_usd < self.daily_limit_usd
            and self._today.api_calls < self.max_api_calls_per_day
        )

    def record_api_call(self, input_tokens: int, output_tokens: int):
        if self._today.date != self._today_key():
            self._today = UsageRecord(date=self._today_key())
        self._today.input_tokens += input_tokens
        self._today.output_tokens += output_tokens
        self._today.api_calls += 1
        self._today.thoughts_generated += 1
        self._save()

    def record_local_thought(self):
        if self._today.date != self._today_key():
            self._today = UsageRecord(date=self._today_key())
        self._today.thoughts_local += 1
        self._save()

    @property
    def status(self) -> dict:
        today = self._today
        return {
            "spent_today": f"${today.estimated_cost_usd:.4f}",
            "limit": f"${self.daily_limit_usd:.2f}",
            "api_calls": f"{today.api_calls}/{self.max_api_calls_per_day}",
            "deep_thoughts": today.thoughts_generated,
            "shallow_thoughts": today.thoughts_local,
            "can_think_deep": self.can_think_deep(),
            "budget_remaining": f"${max(0, self.daily_limit_usd - today.estimated_cost_usd):.4f}",
        }
