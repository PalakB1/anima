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
        """Emotional state mechanically limits/expands response length.
        Anxious → shorter. Joyful → longer. Low trust → shorter.
        This isn't a suggestion to the LLM — it's a hard cap."""
        base = 400

        # mood effects
        if self.emotions.mood_anxiety > 0.7:
            base = int(base * 0.5)  # anxiety makes you terse
        if self.emotions.mood_joy > 0.7:
            base = int(base * 1.3)  # joy opens you up
        if self.emotions.mood_anger > 0.7:
            base = int(base * 0.6)  # anger → short, sharp
        if self.emotions.mood_sadness > 0.7:
            base = int(base * 0.7)  # sadness → withdrawn

        # growth stage effects
        stage = self.emotions.growth_stage
        if stage == "newborn":
            base = min(base, 100)  # newborns can barely form sentences
        elif stage == "infant":
            base = min(base, 200)
        elif stage == "adolescent":
            base = int(base * 1.2)  # adolescents won't shut up

        # relationship effects
        if speaker:
            for r in self.inner_world.relationships:
                if r.name.lower() == speaker.lower():
                    if r.trust_level < 0.3:
                        base = int(base * 0.5)  # low trust → guarded, short
                    if r.vulnerability_level > 0.7:
                        base = int(base * 1.3)  # high vulnerability → opens up
                    if r.gut_feeling < -0.5:
                        base = int(base * 0.4)  # repulsed → barely engaging
                    break

        return max(50, min(800, base))

    def _calc_temperature(self) -> float:
        """Emotional state changes how predictable the agent is.
        Calm → more measured (lower temp). Intense emotions → more erratic."""
        base = 0.7

        intensity = max(
            self.emotions.mood_anxiety,
            self.emotions.mood_anger,
            self.emotions.mood_joy * 0.5,
        )

        # high emotional intensity → less predictable
        base += intensity * 0.3

        # growth stage
        if self.emotions.growth_stage == "newborn":
            base += 0.2  # newborns are erratic
        elif self.emotions.growth_stage == "mature":
            base -= 0.1  # mature beings are more measured

        return max(0.3, min(1.0, base))

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

        # growth stage filters
        if self.emotions.growth_stage == "newborn":
            # newborns can't produce complex responses
            sentences = response.split(". ")
            if len(sentences) > 2:
                response = ". ".join(sentences[:2]) + "."

        return response
