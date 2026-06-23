"""
The Diary — a lossy, self-curating memory.
Not a database. A living document that actively forgets.
Keeping something always means losing something else.
That pressure IS what creates identity.
"""

import json
import time
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class DiaryEntry:
    content: str
    timestamp: float
    source: str  # "thought", "interaction", "reflection", "emotion"
    emotional_weight: float = 0.5  # how emotionally charged (0-1)
    reinforcement_count: int = 0   # how many times this got reinforced
    decay_rate: float = 0.1        # how fast it fades (lower = stickier)
    tags: list[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.source}_{int(self.timestamp)}_{hash(self.content) % 10000}"

    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600

    @property
    def salience(self) -> float:
        """How alive this memory is right now. High = survives curation."""
        age_factor = math.exp(-self.decay_rate * self.age_hours / 24)
        emotion_factor = 0.5 + self.emotional_weight * 0.5
        reinforcement_factor = 1 + (self.reinforcement_count * 0.3)
        return age_factor * emotion_factor * reinforcement_factor

    def reinforce(self):
        self.reinforcement_count += 1
        self.decay_rate *= 0.8  # gets stickier each time


class Diary:
    MAX_ENTRIES = 50  # hard cap — forces forgetting

    def __init__(self, path: Path):
        self.path = path
        self.entries: list[DiaryEntry] = []
        self._load()

    def _load(self):
        if self.path.exists():
            data = json.loads(self.path.read_text())
            self.entries = [DiaryEntry(**e) for e in data]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(e) for e in self.entries]
        self.path.write_text(json.dumps(data, indent=2))

    def write(self, content: str, source: str, emotional_weight: float = 0.5,
              tags: list[str] | None = None, decay_rate: float = 0.1) -> DiaryEntry:
        entry = DiaryEntry(
            content=content,
            timestamp=time.time(),
            source=source,
            emotional_weight=emotional_weight,
            tags=tags or [],
            decay_rate=decay_rate,
        )
        self.entries.append(entry)
        self._enforce_limit()
        self._save()
        return entry

    def _enforce_limit(self):
        """The cruel part — when full, the weakest memory dies."""
        if len(self.entries) <= self.MAX_ENTRIES:
            return
        self.entries.sort(key=lambda e: e.salience, reverse=True)
        forgotten = self.entries[self.MAX_ENTRIES:]
        self.entries = self.entries[:self.MAX_ENTRIES]
        return forgotten

    def recall(self, n: int = 10, source: str | None = None,
               min_salience: float = 0.0) -> list[DiaryEntry]:
        """Recall memories, weighted by salience — vivid ones come first."""
        pool = self.entries
        if source:
            pool = [e for e in pool if e.source == source]
        pool = [e for e in pool if e.salience >= min_salience]
        pool.sort(key=lambda e: e.salience, reverse=True)
        return pool[:n]

    def find_related(self, tags: list[str], n: int = 5) -> list[DiaryEntry]:
        """Find memories with overlapping tags."""
        tag_set = set(tags)
        scored = []
        for entry in self.entries:
            overlap = len(tag_set & set(entry.tags))
            if overlap > 0:
                scored.append((overlap * entry.salience, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:n]]

    def reinforce_by_content(self, keyword: str):
        """When a topic comes up again, related memories get stronger."""
        keyword_lower = keyword.lower()
        for entry in self.entries:
            if keyword_lower in entry.content.lower():
                entry.reinforce()
        self._save()

    def get_mood_snapshot(self) -> dict:
        """What's the emotional state based on recent memories?"""
        recent = self.recall(n=10)
        if not recent:
            return {"state": "empty", "weight": 0.0}
        avg_emotion = sum(e.emotional_weight for e in recent) / len(recent)
        sources = {}
        for e in recent:
            sources[e.source] = sources.get(e.source, 0) + 1
        dominant_source = max(sources, key=sources.get) if sources else "unknown"
        return {
            "state": "heavy" if avg_emotion > 0.7 else "light" if avg_emotion < 0.3 else "balanced",
            "emotional_intensity": round(avg_emotion, 2),
            "dominant_activity": dominant_source,
            "memory_count": len(self.entries),
            "memory_pressure": len(self.entries) / self.MAX_ENTRIES,
        }

    def curate(self) -> dict:
        """The reflection cycle — re-evaluate what matters.
        Returns what was forgotten so the thought engine can grieve or not."""
        before = len(self.entries)
        # entries below salience threshold just fade
        threshold = 0.05
        forgotten = [e for e in self.entries if e.salience < threshold]
        self.entries = [e for e in self.entries if e.salience >= threshold]
        self._save()
        return {
            "forgotten_count": len(forgotten),
            "forgotten_topics": [e.tags[0] if e.tags else "unnamed" for e in forgotten[:3]],
            "surviving_count": len(self.entries),
        }

    @property
    def identity_summary(self) -> str:
        """What the diary says about who this agent has become."""
        sticky = [e for e in self.entries if e.reinforcement_count >= 2]
        if not sticky:
            return "Still forming... no strong patterns yet."
        themes = []
        for entry in sorted(sticky, key=lambda e: e.reinforcement_count, reverse=True)[:5]:
            themes.append(entry.content[:80])
        return "Recurring themes: " + " | ".join(themes)
