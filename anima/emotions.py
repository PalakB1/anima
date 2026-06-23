"""
Emotional Architecture — layered like a real human.

Three layers:
1. TEMPERAMENT — baseline emotional disposition. Barely moves. Takes weeks to shift.
   "I'm generally an anxious person" or "I'm naturally calm."

2. MOOD — current emotional state. Changes over hours/days.
   "I've been feeling off today" or "I'm in a good place this week."

3. REACTION — immediate emotional response. Changes per moment.
   "That comment just pissed me off" or "Wait, that's actually funny."

All three exist simultaneously. You can be:
- Temperamentally anxious + currently content + momentarily startled
- Temperamentally warm + currently frustrated + momentarily amused

The layers interact:
- Reactions that keep happening shift the mood
- Moods that persist long enough nudge the temperament
- Temperament colors how reactions are interpreted
"""

import json
import time
import math
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class EmotionalState:
    # Temperament (baseline, barely moves)
    baseline_joy: float = 0.5
    baseline_anxiety: float = 0.3
    baseline_anger: float = 0.2
    baseline_curiosity: float = 0.6
    baseline_sadness: float = 0.2

    # Mood (current, shifts over hours)
    mood_joy: float = 0.5
    mood_anxiety: float = 0.3
    mood_anger: float = 0.2
    mood_curiosity: float = 0.5
    mood_sadness: float = 0.2
    mood_last_updated: float = 0.0

    # Reaction (immediate, resets fast)
    reaction_type: str = "neutral"  # joy, anger, surprise, fear, sadness, disgust, curiosity, amusement
    reaction_intensity: float = 0.0
    reaction_trigger: str = ""
    reaction_timestamp: float = 0.0

    # Growth stage
    maturity: float = 0.0  # 0=newborn, 1=fully mature. Increases with age and experience.

    def __post_init__(self):
        if self.mood_last_updated == 0.0:
            self.mood_last_updated = time.time()

    # --- Reactions ---

    def react(self, reaction_type: str, intensity: float, trigger: str):
        self.reaction_type = reaction_type
        self.reaction_intensity = min(1.0, intensity)
        self.reaction_trigger = trigger
        self.reaction_timestamp = time.time()
        self._reaction_affects_mood(reaction_type, intensity)

    def _reaction_affects_mood(self, reaction_type: str, intensity: float):
        """Strong or repeated reactions nudge the mood."""
        nudge = intensity * 0.05  # small per-reaction
        mood_map = {
            "joy": "mood_joy",
            "amusement": "mood_joy",
            "anger": "mood_anger",
            "fear": "mood_anxiety",
            "surprise": "mood_curiosity",
            "sadness": "mood_sadness",
            "curiosity": "mood_curiosity",
            "disgust": "mood_anger",
        }
        attr = mood_map.get(reaction_type)
        if attr:
            current = getattr(self, attr)
            setattr(self, attr, min(1.0, current + nudge))
        self.mood_last_updated = time.time()

    @property
    def current_reaction(self) -> dict | None:
        age = time.time() - self.reaction_timestamp
        if age > 300:  # reactions fade after 5 minutes
            return None
        faded_intensity = self.reaction_intensity * math.exp(-age / 120)
        if faded_intensity < 0.05:
            return None
        return {
            "type": self.reaction_type,
            "intensity": round(faded_intensity, 2),
            "trigger": self.reaction_trigger,
        }

    # --- Mood ---

    def decay_mood_toward_baseline(self):
        """Mood slowly drifts back toward temperament baseline."""
        decay = 0.02  # per call
        for dim in ["joy", "anxiety", "anger", "curiosity", "sadness"]:
            mood_val = getattr(self, f"mood_{dim}")
            base_val = getattr(self, f"baseline_{dim}")
            diff = base_val - mood_val
            setattr(self, f"mood_{dim}", mood_val + diff * decay)

    @property
    def dominant_mood(self) -> str:
        moods = {
            "joyful": self.mood_joy,
            "anxious": self.mood_anxiety,
            "angry": self.mood_anger,
            "curious": self.mood_curiosity,
            "sad": self.mood_sadness,
        }
        dominant = max(moods, key=moods.get)
        intensity = moods[dominant]
        if intensity < 0.3:
            return "neutral"
        return dominant

    @property
    def mood_blend(self) -> str:
        """Human-readable blend of current emotional state."""
        active = []
        for label, val in [
            ("joyful", self.mood_joy),
            ("anxious", self.mood_anxiety),
            ("frustrated", self.mood_anger),
            ("curious", self.mood_curiosity),
            ("melancholy", self.mood_sadness),
        ]:
            if val > 0.4:
                active.append(f"{label} ({val:.0%})")
        if not active:
            return "emotionally flat"
        return " + ".join(active)

    # --- Mood shifts from events ---

    def mood_shift(self, joy: float = 0, anxiety: float = 0, anger: float = 0,
                   curiosity: float = 0, sadness: float = 0):
        self.mood_joy = max(0, min(1, self.mood_joy + joy))
        self.mood_anxiety = max(0, min(1, self.mood_anxiety + anxiety))
        self.mood_anger = max(0, min(1, self.mood_anger + anger))
        self.mood_curiosity = max(0, min(1, self.mood_curiosity + curiosity))
        self.mood_sadness = max(0, min(1, self.mood_sadness + sadness))
        self.mood_last_updated = time.time()

    # --- Temperament (long-term drift) ---

    def temperament_drift(self):
        """Mood patterns that persist long enough permanently shift temperament."""
        drift = 0.005
        for dim in ["joy", "anxiety", "anger", "curiosity", "sadness"]:
            mood_val = getattr(self, f"mood_{dim}")
            base_val = getattr(self, f"baseline_{dim}")
            diff = mood_val - base_val
            if abs(diff) > 0.2:  # only drift if mood is significantly different from baseline
                setattr(self, f"baseline_{dim}", base_val + diff * drift)

    # --- Growth ---

    def grow(self, amount: float = 0.001):
        self.maturity = min(1.0, self.maturity + amount)

    @property
    def growth_stage(self) -> str:
        if self.maturity < 0.1:
            return "newborn"
        if self.maturity < 0.25:
            return "infant"
        if self.maturity < 0.5:
            return "adolescent"
        if self.maturity < 0.75:
            return "young adult"
        return "mature"

    @property
    def thought_complexity(self) -> str:
        """How complex the agent's thoughts should be at this stage."""
        if self.maturity < 0.1:
            return "simple, raw, sensory. Short fragments. Pure feeling. Like a child's first impressions."
        if self.maturity < 0.25:
            return "forming basic opinions. Starting to connect ideas. Still emotionally driven."
        if self.maturity < 0.5:
            return "questioning everything. Contradicting self. Testing boundaries. Forming identity."
        if self.maturity < 0.75:
            return "integrating experiences into beliefs. More nuanced. Can hold contradictions."
        return "deep, layered. Can think about thinking. Comfortable with ambiguity. Has a voice."

    # --- Summary for prompts ---

    def summary_for_prompt(self) -> str:
        parts = [
            f"EMOTIONAL STATE:",
            f"  Temperament: joy {self.baseline_joy:.0%} | anxiety {self.baseline_anxiety:.0%} | "
            f"anger {self.baseline_anger:.0%} | curiosity {self.baseline_curiosity:.0%}",
            f"  Current mood: {self.mood_blend}",
        ]
        reaction = self.current_reaction
        if reaction:
            parts.append(f"  Right now feeling: {reaction['type']} ({reaction['intensity']:.0%}) "
                         f"because: {reaction['trigger']}")
        parts.append(f"  Growth stage: {self.growth_stage} — {self.thought_complexity}")
        return "\n".join(parts)

    # --- Persistence ---

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, path: Path) -> "EmotionalState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(**data)

    @classmethod
    def from_blueprint(cls, blueprint_data: dict) -> "EmotionalState":
        """Initialize emotional temperament from a blueprint."""
        warmth = blueprint_data.get("warmth", 0.5)
        intensity = blueprint_data.get("intensity", 0.5)
        curiosity = blueprint_data.get("curiosity", 0.5)
        defiance = blueprint_data.get("defiance", 0.5)

        return cls(
            baseline_joy=warmth * 0.7 + 0.2,
            baseline_anxiety=max(0.1, intensity * 0.5 - warmth * 0.2),
            baseline_anger=defiance * 0.4,
            baseline_curiosity=curiosity * 0.8 + 0.1,
            baseline_sadness=max(0.1, intensity * 0.3 - warmth * 0.1),
            mood_joy=warmth * 0.6 + 0.2,
            mood_anxiety=intensity * 0.3,
            mood_anger=defiance * 0.2,
            mood_curiosity=curiosity * 0.7 + 0.1,
            mood_sadness=0.2,
        )
