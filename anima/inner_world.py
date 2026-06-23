"""
The Inner World — beliefs, lessons, desires, and deep relationship models.
"""

import json
import time
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Belief:
    content: str
    confidence: float
    formed_from: str
    times_reinforced: int = 0
    times_contradicted: int = 0
    formed_at: float = 0.0

    def __post_init__(self):
        if self.formed_at == 0.0:
            self.formed_at = time.time()

    @property
    def stability(self) -> float:
        total = self.times_reinforced + self.times_contradicted
        if total == 0:
            return 0.5
        return self.times_reinforced / total

    def reinforce(self):
        self.times_reinforced += 1
        self.confidence = min(1.0, self.confidence + 0.05)

    def contradict(self):
        self.times_contradicted += 1
        self.confidence = max(0.0, self.confidence - 0.1)


@dataclass
class Relationship:
    name: str
    model: str                       # cognitive understanding: "direct, values honesty"

    # --- Emotional core ---
    gut_feeling: float = 0.5         # -1 (repulsion) to 1 (attraction). The irrational like/dislike.
    emotional_deposits: list[dict] = field(default_factory=list)  # [{emotion, intensity, context, timestamp}]
    dominant_emotion: str = "neutral" # what this person MAKES them feel most often

    # --- Trust & safety ---
    trust_level: float = 0.5
    vulnerability_level: float = 0.2  # how open they are with this person (earned, not given)
    predictability: float = 0.5       # how well they can predict this person's behavior

    # --- Behavioral adaptation ---
    communication_style: str = ""     # how they've learned to talk to THIS person
    topics_safe: list[str] = field(default_factory=list)      # topics that go well
    topics_avoid: list[str] = field(default_factory=list)     # topics that cause friction
    triggers: list[str] = field(default_factory=list)         # "when they say X, it means Y"

    # --- Patterns ---
    learned_patterns: list[str] = field(default_factory=list)
    interaction_count: int = 0
    last_interaction: float = 0.0
    emotional_valence: float = 0.5

    # --- History ---
    memorable_moments: list[str] = field(default_factory=list)  # key moments that shaped the relationship

    def deposit_emotion(self, emotion: str, intensity: float, context: str):
        """Every interaction leaves an emotional residue."""
        self.emotional_deposits.append({
            "emotion": emotion,
            "intensity": intensity,
            "context": context,
            "timestamp": time.time(),
        })
        # keep only recent deposits (memory fades)
        if len(self.emotional_deposits) > 30:
            self.emotional_deposits = self.emotional_deposits[-30:]

        # update gut feeling based on accumulated deposits
        self._recalculate_gut()
        # update dominant emotion
        self._recalculate_dominant_emotion()

    def _recalculate_gut(self):
        """Gut feeling = weighted average of emotional deposits. Recent ones matter more."""
        if not self.emotional_deposits:
            return

        positive = {"joy", "amusement", "curiosity", "warmth", "gratitude", "excitement", "comfort"}
        negative = {"anger", "anxiety", "sadness", "disgust", "fear", "frustration", "contempt", "boredom"}

        weighted_sum = 0.0
        weight_total = 0.0
        now = time.time()

        for dep in self.emotional_deposits:
            age_hours = (now - dep["timestamp"]) / 3600
            recency_weight = math.exp(-age_hours / 72)  # 3-day half-life
            weight = dep["intensity"] * recency_weight

            if dep["emotion"] in positive:
                weighted_sum += weight
            elif dep["emotion"] in negative:
                weighted_sum -= weight
            weight_total += weight

        if weight_total > 0:
            self.gut_feeling = max(-1.0, min(1.0, weighted_sum / weight_total))

    def _recalculate_dominant_emotion(self):
        """What emotion does this person trigger most often?"""
        if not self.emotional_deposits:
            self.dominant_emotion = "neutral"
            return

        # count recent emotions weighted by intensity
        counts: dict[str, float] = {}
        for dep in self.emotional_deposits[-15:]:
            e = dep["emotion"]
            counts[e] = counts.get(e, 0) + dep["intensity"]

        self.dominant_emotion = max(counts, key=counts.get) if counts else "neutral"

    def update_after_interaction(self, model_update: str, trust_delta: float,
                                valence: float, pattern: str | None = None,
                                communication_note: str | None = None,
                                safe_topic: str | None = None,
                                avoid_topic: str | None = None,
                                trigger: str | None = None,
                                memorable: str | None = None):
        self.interaction_count += 1
        self.last_interaction = time.time()
        if model_update:
            self.model = model_update
        self.trust_level = max(0.0, min(1.0, self.trust_level + trust_delta))
        self.emotional_valence = valence

        # vulnerability grows slowly with positive interactions, drops fast with negative
        if trust_delta > 0:
            self.vulnerability_level = min(1.0, self.vulnerability_level + trust_delta * 0.3)
        elif trust_delta < 0:
            self.vulnerability_level = max(0.0, self.vulnerability_level + trust_delta * 0.8)

        # predictability increases with interactions
        self.predictability = min(1.0, self.predictability + 0.02)

        if pattern and pattern not in self.learned_patterns:
            self.learned_patterns.append(pattern)
            if len(self.learned_patterns) > 10:
                self.learned_patterns = self.learned_patterns[-10:]

        if communication_note:
            self.communication_style = communication_note

        if safe_topic and safe_topic not in self.topics_safe:
            self.topics_safe.append(safe_topic)
            if len(self.topics_safe) > 8:
                self.topics_safe = self.topics_safe[-8:]

        if avoid_topic and avoid_topic not in self.topics_avoid:
            self.topics_avoid.append(avoid_topic)
            if len(self.topics_avoid) > 5:
                self.topics_avoid = self.topics_avoid[-5:]

        if trigger and trigger not in self.triggers:
            self.triggers.append(trigger)
            if len(self.triggers) > 5:
                self.triggers = self.triggers[-5:]

        if memorable and memorable not in self.memorable_moments:
            self.memorable_moments.append(memorable)
            if len(self.memorable_moments) > 10:
                self.memorable_moments = self.memorable_moments[-10:]

    @property
    def feeling_label(self) -> str:
        """Human-readable gut feeling."""
        if self.gut_feeling > 0.6:
            return "drawn to"
        if self.gut_feeling > 0.2:
            return "warm toward"
        if self.gut_feeling > -0.2:
            return "neutral about"
        if self.gut_feeling > -0.6:
            return "uneasy around"
        return "repelled by"

    @property
    def openness_label(self) -> str:
        if self.vulnerability_level > 0.7:
            return "fully open"
        if self.vulnerability_level > 0.4:
            return "somewhat guarded"
        if self.vulnerability_level > 0.2:
            return "guarded"
        return "walls up"


@dataclass
class Lesson:
    situation: str
    behavior_tried: str
    outcome: str
    learned_approach: str
    confidence: float = 0.5
    times_applied: int = 0
    times_worked: int = 0

    @property
    def effectiveness(self) -> float:
        if self.times_applied == 0:
            return 0.5
        return self.times_worked / self.times_applied

    def applied(self, worked: bool):
        self.times_applied += 1
        if worked:
            self.times_worked += 1
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.confidence = max(0.0, self.confidence - 0.15)


@dataclass
class Desire:
    content: str
    urgency: float = 0.5
    source: str = "reflection"
    created_at: float = 0.0
    satisfied: bool = False

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class InnerWorld:
    MAX_BELIEFS = 20
    MAX_LESSONS = 15
    MAX_DESIRES = 10
    MAX_RELATIONSHIPS = 20

    def __init__(self, path: Path):
        self.path = path
        self.beliefs: list[Belief] = []
        self.relationships: list[Relationship] = []
        self.lessons: list[Lesson] = []
        self.desires: list[Desire] = []
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text())
        self.beliefs = [Belief(**b) for b in data.get("beliefs", [])]
        self.relationships = [Relationship(**r) for r in data.get("relationships", [])]
        self.lessons = [Lesson(**l) for l in data.get("lessons", [])]
        self.desires = [Desire(**d) for d in data.get("desires", [])]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "beliefs": [asdict(b) for b in self.beliefs],
            "relationships": [asdict(r) for r in self.relationships],
            "lessons": [asdict(l) for l in self.lessons],
            "desires": [asdict(d) for d in self.desires],
        }
        self.path.write_text(json.dumps(data, indent=2))

    # --- Beliefs ---

    def add_belief(self, content: str, confidence: float, formed_from: str):
        for b in self.beliefs:
            if self._similar(b.content, content):
                b.reinforce()
                self._save()
                return b
        belief = Belief(content=content, confidence=confidence, formed_from=formed_from)
        self.beliefs.append(belief)
        if len(self.beliefs) > self.MAX_BELIEFS:
            self.beliefs.sort(key=lambda b: b.confidence * b.stability, reverse=True)
            self.beliefs = self.beliefs[:self.MAX_BELIEFS]
        self._save()
        return belief

    def contradict_belief(self, keyword: str):
        for b in self.beliefs:
            if keyword.lower() in b.content.lower():
                b.contradict()
                if b.confidence < 0.1:
                    self.beliefs.remove(b)
        self._save()

    def get_beliefs(self, min_confidence: float = 0.3) -> list[Belief]:
        return [b for b in self.beliefs if b.confidence >= min_confidence]

    # --- Relationships ---

    def get_or_create_relationship(self, name: str) -> Relationship:
        for r in self.relationships:
            if r.name.lower() == name.lower():
                return r
        rel = Relationship(name=name, model="unknown — just met")
        self.relationships.append(rel)
        if len(self.relationships) > self.MAX_RELATIONSHIPS:
            self.relationships.sort(key=lambda r: r.interaction_count, reverse=True)
            self.relationships = self.relationships[:self.MAX_RELATIONSHIPS]
        self._save()
        return rel

    def update_relationship(self, name: str, model: str, trust_delta: float = 0.0,
                            valence: float = 0.5, pattern: str | None = None,
                            emotion: str | None = None, emotion_intensity: float = 0.3,
                            emotion_context: str = "",
                            communication_note: str | None = None,
                            safe_topic: str | None = None,
                            avoid_topic: str | None = None,
                            trigger: str | None = None,
                            memorable: str | None = None):
        rel = self.get_or_create_relationship(name)
        rel.update_after_interaction(
            model_update=model, trust_delta=trust_delta, valence=valence,
            pattern=pattern, communication_note=communication_note,
            safe_topic=safe_topic, avoid_topic=avoid_topic,
            trigger=trigger, memorable=memorable,
        )
        if emotion:
            rel.deposit_emotion(emotion, emotion_intensity, emotion_context or "interaction")
        self._save()
        return rel

    # --- Lessons ---

    def add_lesson(self, situation: str, behavior_tried: str, outcome: str,
                   learned_approach: str, confidence: float = 0.5):
        lesson = Lesson(situation=situation, behavior_tried=behavior_tried,
                        outcome=outcome, learned_approach=learned_approach, confidence=confidence)
        self.lessons.append(lesson)
        if len(self.lessons) > self.MAX_LESSONS:
            self.lessons.sort(key=lambda l: l.effectiveness * l.confidence, reverse=True)
            self.lessons = self.lessons[:self.MAX_LESSONS]
        self._save()
        return lesson

    def get_relevant_lessons(self, situation_keywords: list[str]) -> list[Lesson]:
        results = []
        for lesson in self.lessons:
            for kw in situation_keywords:
                if kw.lower() in lesson.situation.lower():
                    results.append(lesson)
                    break
        return results

    # --- Desires ---

    def add_desire(self, content: str, urgency: float = 0.5, source: str = "reflection"):
        for d in self.desires:
            if self._similar(d.content, content):
                d.urgency = min(1.0, d.urgency + 0.1)
                self._save()
                return d
        desire = Desire(content=content, urgency=urgency, source=source)
        self.desires.append(desire)
        if len(self.desires) > self.MAX_DESIRES:
            self.desires.sort(key=lambda d: d.urgency, reverse=True)
            self.desires = self.desires[:self.MAX_DESIRES]
        self._save()
        return desire

    def satisfy_desire(self, keyword: str):
        for d in self.desires:
            if keyword.lower() in d.content.lower():
                d.satisfied = True
                d.urgency *= 0.3
        self._save()

    def active_desires(self) -> list[Desire]:
        return [d for d in self.desires if not d.satisfied and d.urgency > 0.2]

    # --- Prompt summaries ---

    def summary_for_prompt(self) -> str:
        parts = []
        beliefs = self.get_beliefs()
        if beliefs:
            parts.append("THINGS I BELIEVE:\n" +
                         "\n".join(f"- \"{b.content}\" ({b.confidence:.0%})" for b in beliefs[:7]))
        desires = self.active_desires()
        if desires:
            parts.append("WHAT I WANT:\n" +
                         "\n".join(f"- {d.content} (urgency: {d.urgency:.0%})" for d in desires[:5]))
        lessons = [l for l in self.lessons if l.confidence > 0.4]
        if lessons:
            parts.append("WHAT I'VE LEARNED:\n" +
                         "\n".join(f"- {l.situation}: {l.learned_approach}" for l in lessons[:5]))
        return "\n\n".join(parts) if parts else "(still figuring things out)"

    def relationship_context(self, name: str) -> str:
        for r in self.relationships:
            if r.name.lower() == name.lower():
                parts = [
                    f"Relationship with {r.name}:",
                    f"  Understanding: {r.model}",
                    f"  Gut feeling: {r.feeling_label} (gut: {r.gut_feeling:+.2f})",
                    f"  Trust: {r.trust_level:.0%} | Openness: {r.openness_label}",
                    f"  They make me feel: {r.dominant_emotion}",
                    f"  Predictability: {r.predictability:.0%} | Interactions: {r.interaction_count}",
                ]
                if r.communication_style:
                    parts.append(f"  How I talk to them: {r.communication_style}")
                if r.topics_safe:
                    parts.append(f"  Safe topics: {', '.join(r.topics_safe[-3:])}")
                if r.topics_avoid:
                    parts.append(f"  Avoid: {', '.join(r.topics_avoid[-3:])}")
                if r.triggers:
                    parts.append(f"  Triggers: {', '.join(r.triggers[-3:])}")
                if r.memorable_moments:
                    parts.append(f"  Key moments: {', '.join(r.memorable_moments[-3:])}")
                if r.learned_patterns:
                    parts.append(f"  Patterns: {', '.join(r.learned_patterns[-3:])}")
                return "\n".join(parts)
        return f"Never met {name} before."

    @staticmethod
    def _similar(a: str, b: str) -> bool:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return False
        return len(a_words & b_words) / max(len(a_words), len(b_words)) > 0.5
