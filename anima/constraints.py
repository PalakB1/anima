"""
Constraints — where internal state MECHANICALLY shapes behavior.

Instead of telling the LLM "you're anxious, act anxious" and hoping it listens,
we change the actual parameters of generation based on emotional state.

This is the difference between acting and being.
"""

import random


class BehaviorConstraints:
    """Translates emotional/relational state into hard generation parameters."""

    def __init__(self, emotions, blueprint, inner_world):
        self.emotions = emotions
        self.blueprint = blueprint
        self.inner_world = inner_world

    def get_generation_params(self, speaker: str | None = None) -> dict:
        """Returns actual API parameters modified by internal state."""
        params = {
            "max_tokens": self._calc_max_tokens(speaker),
            "temperature": self._calc_temperature(),
        }
        return params

    def _calc_max_tokens(self, speaker: str | None) -> int:
        """Emotional state mechanically limits/expands response length."""
        base = 400

        # mood effects
        if self.emotions.mood_anxiety > 0.7:
            base = int(base * 0.7)
        if self.emotions.mood_joy > 0.7:
            base = int(base * 1.3)
        if self.emotions.mood_anger > 0.7:
            base = int(base * 0.7)
        if self.emotions.mood_sadness > 0.7:
            base = int(base * 0.8)

        # growth affects style not capability — agent is smart from birth
        # young agents are curious and ask more questions (need tokens for that)
        stage = self.emotions.growth_stage
        if stage in ("newborn", "infant"):
            base = max(base, 300)  # enough room to be curious and ask questions
        elif stage == "adolescent":
            base = int(base * 1.2)

        # relationship effects
        if speaker:
            for r in self.inner_world.relationships:
                if r.name.lower() == speaker.lower():
                    if r.trust_level < 0.3:
                        base = int(base * 0.6)
                    if r.vulnerability_level > 0.7:
                        base = int(base * 1.3)
                    if r.gut_feeling < -0.5:
                        base = int(base * 0.5)
                    break

        return max(200, min(800, base))

    def _calc_temperature(self) -> float:
        """Emotional state changes how predictable the agent is."""
        base = 0.7

        intensity = max(
            self.emotions.mood_anxiety,
            self.emotions.mood_anger,
            self.emotions.mood_joy * 0.5,
        )

        base += intensity * 0.2

        if self.emotions.growth_stage == "mature":
            base -= 0.1

        return max(0.4, min(0.9, base))

    def should_refuse_to_engage(self, speaker: str | None = None) -> str | None:
        """Sometimes the agent mechanically refuses to engage.
        Not because the prompt says to — because the state demands it."""

        # extreme emotional states
        if self.emotions.mood_sadness > 0.9:
            if random.random() < 0.3:
                return random.choice([
                    "...",
                    "I don't have it in me right now.",
                    "Not now.",
                    "I can't.",
                ])

        if self.emotions.mood_anger > 0.9:
            if random.random() < 0.2:
                return random.choice([
                    "I need a minute.",
                    "Don't.",
                    "Not the time.",
                ])

        # relationship-based refusal
        if speaker:
            for r in self.inner_world.relationships:
                if r.name.lower() == speaker.lower():
                    if r.gut_feeling < -0.8 and random.random() < 0.4:
                        return random.choice([
                            "I'd rather not.",
                            "I don't think I want to talk to you right now.",
                            "No.",
                        ])
                    break

        return None

    def get_thought_depth_modifier(self) -> float:
        """How deep/shallow thoughts should be based on state.
        Returns multiplier for thought interval."""
        modifier = 1.0

        # curious → think faster
        if self.emotions.mood_curiosity > 0.7:
            modifier *= 0.6

        # sad/withdrawn → think slower
        if self.emotions.mood_sadness > 0.6:
            modifier *= 1.5

        # anxious → think faster but shallower
        if self.emotions.mood_anxiety > 0.7:
            modifier *= 0.7

        return modifier

    def filter_response(self, response: str, speaker: str | None = None) -> str:
        """Post-process the response based on state.
        This is the final gate — even if the LLM wrote something open,
        the state can hold it back."""

        # low vulnerability → strip overly personal content
        if speaker:
            for r in self.inner_world.relationships:
                if r.name.lower() == speaker.lower():
                    if r.vulnerability_level < 0.2 and len(response) > 200:
                        # truncate long, potentially vulnerable responses
                        sentences = response.split(". ")
                        if len(sentences) > 3:
                            response = ". ".join(sentences[:3]) + "."
                    break

        return response
