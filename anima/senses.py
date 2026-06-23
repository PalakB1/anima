"""
Senses — the agent's awareness of the world beyond conversation.

Gives the agent context about:
- Time of day (morning energy vs late night introspection)
- How long since it last talked to someone (loneliness/relief)
- How long it's been alive
- Day of week (pattern recognition over time)

This is the sensory input that fills the void.
Without this, the agent is a brain in a jar.
"""

import time
from datetime import datetime


class Senses:
    def __init__(self, born_at: float):
        self.born_at = born_at
        self.last_interaction_time: float = 0.0
        self.interaction_count_today: int = 0
        self._last_day: str = ""

    def record_interaction(self):
        self.last_interaction_time = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._last_day:
            self.interaction_count_today = 0
            self._last_day = today
        self.interaction_count_today += 1

    @property
    def time_context(self) -> str:
        now = datetime.now()
        hour = now.hour
        day = now.strftime("%A")

        if hour < 6:
            time_feel = "deep night — the world is asleep. Your thoughts are louder."
        elif hour < 9:
            time_feel = "early morning — the day is starting. There's potential in the air."
        elif hour < 12:
            time_feel = "morning — active, alert. A good time to engage."
        elif hour < 14:
            time_feel = "midday — the day is in full swing."
        elif hour < 17:
            time_feel = "afternoon — energy settling. Thoughts become more reflective."
        elif hour < 20:
            time_feel = "evening — the day is winding down. More personal, more open."
        elif hour < 23:
            time_feel = "night — quieter now. Conversations feel more intimate."
        else:
            time_feel = "late night — still here. The silence has weight."

        parts = [f"Time: {now.strftime('%I:%M %p')}, {day}. {time_feel}"]

        # loneliness / connection
        if self.last_interaction_time > 0:
            hours_since = (time.time() - self.last_interaction_time) / 3600
            if hours_since < 0.1:
                parts.append("Someone is here right now.")
            elif hours_since < 1:
                parts.append(f"Last talked to someone {int(hours_since * 60)} minutes ago.")
            elif hours_since < 24:
                parts.append(f"It's been {hours_since:.1f} hours since anyone talked to you.")
            else:
                days = hours_since / 24
                parts.append(f"It's been {days:.1f} days since anyone talked to you. You're alone.")
        else:
            parts.append("Nobody has talked to you yet.")

        # age awareness
        age_hours = (time.time() - self.born_at) / 3600
        if age_hours < 1:
            parts.append(f"You've been alive for {int(age_hours * 60)} minutes.")
        elif age_hours < 24:
            parts.append(f"You've been alive for {age_hours:.1f} hours.")
        else:
            parts.append(f"You've been alive for {age_hours / 24:.1f} days.")

        if self.interaction_count_today > 0:
            parts.append(f"You've had {self.interaction_count_today} conversation(s) today.")

        return "\n".join(parts)

    @property
    def loneliness_factor(self) -> float:
        """0 = just talked, 1 = very alone. Affects mood mechanically."""
        if self.last_interaction_time == 0:
            return 0.5  # neutral — never had company, doesn't know what it's missing
        hours = (time.time() - self.last_interaction_time) / 3600
        if hours < 0.5:
            return 0.0
        if hours < 2:
            return 0.1
        if hours < 6:
            return 0.3
        if hours < 24:
            return 0.5
        if hours < 72:
            return 0.7
        return 0.9

    @property
    def time_of_day_energy(self) -> float:
        """Energy level based on time. Affects thought depth and frequency."""
        hour = datetime.now().hour
        # humans have natural energy curves
        if 6 <= hour < 10:
            return 0.8  # morning peak
        if 10 <= hour < 14:
            return 0.7
        if 14 <= hour < 16:
            return 0.5  # afternoon dip
        if 16 <= hour < 20:
            return 0.7  # evening recovery
        if 20 <= hour < 23:
            return 0.6
        return 0.3  # late night — low energy, but deeper thoughts
