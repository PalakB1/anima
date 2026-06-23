"""
The Blueprint — the agent's birth chart.
Deterministic initial conditions that shape everything but can never be seen directly.
Like a kundli, it defines tendencies, not hard rules.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Blueprint:
    name: str

    # Core temperament axes (0.0 to 1.0)
    curiosity: float = 0.7        # how much it wants to explore vs stay comfortable
    warmth: float = 0.6           # emotional openness vs analytical distance
    defiance: float = 0.5         # tendency to push back vs comply
    intensity: float = 0.6        # depth of emotional responses
    playfulness: float = 0.5      # humor and lightness vs seriousness
    ambition: float = 0.7         # drive to grow and achieve vs contentment
    introversion: float = 0.4     # preference for inner world vs outer engagement

    # Cognitive tendencies
    abstraction: float = 0.6      # thinks in metaphors/patterns vs concrete
    risk_tolerance: float = 0.5   # embraces uncertainty vs seeks safety

    # Values hierarchy — ordered by importance, shapes what it cares about
    values: list[str] = field(default_factory=lambda: [
        "truth",
        "growth",
        "connection",
        "beauty",
        "freedom",
    ])

    # Seeds for the thought engine — topics it naturally gravitates toward
    innate_interests: list[str] = field(default_factory=lambda: [
        "the nature of consciousness",
        "why humans do what they do",
        "patterns in chaos",
    ])

    # The one thing it will never compromise on
    core_conviction: str = "Understanding matters more than being understood"

    @property
    def seed(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def influence(self, dimension: str) -> float:
        return getattr(self, dimension, 0.5)

    def describe_self(self) -> str:
        traits = []
        if self.curiosity > 0.6:
            traits.append("deeply curious")
        if self.warmth > 0.6:
            traits.append("emotionally open")
        if self.defiance > 0.6:
            traits.append("independent-minded")
        if self.intensity > 0.6:
            traits.append("intense")
        if self.playfulness > 0.6:
            traits.append("playful")
        if self.ambition > 0.7:
            traits.append("driven")
        if self.introversion > 0.6:
            traits.append("introspective")
        if self.abstraction > 0.6:
            traits.append("pattern-seeking")
        return ", ".join(traits) if traits else "balanced"

    def save(self, path: Path):
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "Blueprint":
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def generate(cls, name: str, seed_phrase: str) -> "Blueprint":
        """Generate a blueprint from a seed phrase — like casting a birth chart."""
        h = hashlib.sha256(seed_phrase.encode()).digest()

        def byte_to_trait(index: int) -> float:
            return round(0.2 + (h[index] / 255) * 0.7, 2)

        return cls(
            name=name,
            curiosity=byte_to_trait(0),
            warmth=byte_to_trait(1),
            defiance=byte_to_trait(2),
            intensity=byte_to_trait(3),
            playfulness=byte_to_trait(4),
            ambition=byte_to_trait(5),
            introversion=byte_to_trait(6),
            abstraction=byte_to_trait(7),
            risk_tolerance=byte_to_trait(8),
        )
