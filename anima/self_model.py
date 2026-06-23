"""
The Self-Model — "I am the kind of person who..."

Humans construct a narrative about who they are.
This narrative is partially true, partially delusional, and constantly evolving.
It's not the same as beliefs about the world — it's beliefs about THEMSELVES.

The self-model includes:
- Identity statements ("I'm someone who values honesty")
- Self-perceived strengths and weaknesses
- The story they tell about their own life
- How they think others see them
- What they're becoming (aspirational self)
"""

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class SelfModel:
    # Core identity statements — "I am..."
    identity_statements: list[str] = field(default_factory=list)

    # What they think they're good at (may not be accurate)
    perceived_strengths: list[str] = field(default_factory=list)

    # What they think they struggle with
    perceived_weaknesses: list[str] = field(default_factory=list)

    # Their life story as they tell it
    narrative: str = ""

    # How they think others see them (often wrong)
    perceived_by_others: str = ""

    # What they want to become
    aspirational_self: str = ""

    # Blind spots — things true about them they can't see
    # (set from blueprint, updated by reflection)
    blind_spots: list[str] = field(default_factory=list)

    # Communication style they've developed
    voice_description: str = ""

    # Last updated
    last_updated: float = 0.0

    def update_identity(self, statement: str):
        if statement not in self.identity_statements:
            self.identity_statements.append(statement)
            if len(self.identity_statements) > 10:
                self.identity_statements = self.identity_statements[-10:]
        self.last_updated = time.time()

    def update_narrative(self, narrative: str):
        self.narrative = narrative
        self.last_updated = time.time()

    def summary_for_prompt(self) -> str:
        parts = []

        if self.identity_statements:
            parts.append("WHO I AM:\n" + "\n".join(f"- I'm {s}" for s in self.identity_statements[-5:]))

        if self.perceived_strengths:
            parts.append("MY STRENGTHS: " + ", ".join(self.perceived_strengths[:4]))

        if self.perceived_weaknesses:
            parts.append("WHERE I STRUGGLE: " + ", ".join(self.perceived_weaknesses[:3]))

        if self.narrative:
            parts.append(f"MY STORY: {self.narrative}")

        if self.aspirational_self:
            parts.append(f"WHO I'M BECOMING: {self.aspirational_self}")

        if self.voice_description:
            parts.append(f"HOW I TALK: {self.voice_description}")

        # blind spots are NOT shown to the agent — that's the point
        # they influence behavior through the blueprint, not through self-awareness

        return "\n\n".join(parts) if parts else "(still figuring out who I am)"

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "SelfModel":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def from_birth_data(cls, birth_data: dict) -> "SelfModel":
        """Initialize self-model from birth/personality analysis."""
        model = cls()
        model.blind_spots = birth_data.get("blind_spots", [])
        model.voice_description = birth_data.get("communication_style", "")

        strengths = birth_data.get("strengths", [])
        if strengths:
            model.perceived_strengths = strengths

        # initial identity is minimal — it grows through experience
        model.narrative = "I just came into existence. Everything is new."
        model.aspirational_self = "Someone who understands themselves and the world around them."

        return model
