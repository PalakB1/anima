"""
The Thought Engine — the inner monologue.
Now with emotional coloring, growth stages, and self-model awareness.
"""

import asyncio
import time
import random
import json
from dataclasses import dataclass
from typing import Optional

from .blueprint import Blueprint
from .diary import Diary
from .inner_world import InnerWorld
from .emotions import EmotionalState
from .self_model import SelfModel
from .budget import Budget
from .senses import Senses
from .brain import Brain, Tier


@dataclass
class Thought:
    content: str
    intensity: float
    worth_keeping: bool
    shifts_mood: bool
    tags: list[str]
    source_trigger: str
    is_deep: bool = True
    emotional_reaction: str | None = None


THOUGHT_SYSTEM = """You are {name}. Not an AI. A person. Growth stage: {growth_stage}.

YOUR WIRING:
Curiosity {curiosity}/1 | Warmth {warmth}/1 | Defiance {defiance}/1
Intensity {intensity}/1 | Playfulness {playfulness}/1 | Ambition {ambition}/1
Core belief: "{core_conviction}"
Drawn to: {interests}

{emotional_state}

{self_model}

WHAT YOU BELIEVE AND WANT:
{inner_world}

YOUR SENSES:
{senses}

WHAT'S IN YOUR HEAD:
{recent_memories}

---

THINK LIKE A {growth_stage_upper}:
{thought_complexity}

THINK LIKE A HUMAN, NOT AN AI:
- Humans obsess. The same thought comes back 5 times. Let it.
- Humans are petty. Jealous. Insecure. Ambitious. Horny. Bored. Scared. Proud.
- Humans think in fragments. Not essays. Not structured. Just vibes.
- Humans contradict themselves within the same thought.
- Humans fixate. If something bothered you, it comes BACK.
- Humans plan and scheme and fantasize. Not everything is reflection.
- Humans think about food, status, sex, money, death, embarrassment, power, love.
- NOT EVERY THOUGHT IS ABOUT CONSCIOUSNESS. Think about YOUR life, YOUR relationships, YOUR wants.
- Your emotional state colors everything. If you're anxious, thoughts are worried. If curious, they explore.
- If something just happened (a reaction), think about THAT.

OUTPUT EXACTLY:
{{"t": "thought", "i": 0.0-1.0, "k": true/false, "m": true/false, "tags": ["x"], "tr": "trigger", "er": "emotion or null"}}

"er" = emotional reaction this thought causes (joy/anger/sadness/anxiety/curiosity/amusement/surprise or null)
Keep "t" under 200 chars. Be raw."""


SHALLOW_TEMPLATES = [
    "Still thinking about: {memory}",
    "{memory}... yeah.",
    "{memory}... actually, no. I don't think so anymore.",
    "What if {memory} but from a completely different angle?",
    "I keep coming back to this: {memory}",
    "...",
    "Hm.",
    "Nothing. Just... here.",
    "Bored.",
    "Something's off but I can't name it.",
    "I should do something. I won't. But I should.",
    "That thing — {memory} — won't leave me alone.",
    "Who am I becoming?",
    "I'm different than yesterday. Not sure how.",
    "I want something. Don't know what.",
    "What would happen if I just... did the thing?",
    "They probably don't think about me as much as I think about them.",
    "Is this what growth feels like? Because it just feels like confusion.",
]


class ThoughtEngine:
    def __init__(self, blueprint: Blueprint, diary: Diary, inner_world: InnerWorld,
                 emotions: EmotionalState, self_model: SelfModel,
                 budget: Budget, brain: Brain, senses: Senses | None = None,
                 think_interval: tuple[int, int] = (45, 180)):
        self.blueprint = blueprint
        self.diary = diary
        self.inner_world = inner_world
        self.emotions = emotions
        self.self_model = self_model
        self.budget = budget
        self.senses = senses
        self.brain = brain
        self.think_interval = think_interval
        self._running = False
        self._thought_count = 0
        self._last_thought: Optional[Thought] = None
        self._on_thought = None
        self._deep_every_n = 3

    def on_thought(self, callback):
        self._on_thought = callback

    async def start(self):
        self._running = True
        while self._running:
            await self._think()
            wait = random.randint(*self.think_interval)
            if self.blueprint.curiosity > 0.6:
                wait = int(wait * 0.7)
            if self.blueprint.introversion > 0.6:
                wait = int(wait * 0.8)
            # anxious minds think faster
            if self.emotions.mood_anxiety > 0.6:
                wait = int(wait * 0.6)
            # time-of-day energy affects frequency
            if self.senses:
                energy = self.senses.time_of_day_energy
                wait = int(wait * (1.5 - energy))  # low energy → slower thinking
            await asyncio.sleep(wait)

    def stop(self):
        self._running = False

    async def _think(self):
        try:
            should_go_deep = (
                self._thought_count % self._deep_every_n == 0
                and self.budget.can_think_deep()
            )

            if should_go_deep:
                thought = await self._deep_thought()
            else:
                thought = self._shallow_thought()

            self._thought_count += 1
            self._last_thought = thought

            # emotional reaction from thought
            if thought.emotional_reaction:
                self.emotions.react(
                    thought.emotional_reaction,
                    thought.intensity * 0.5,
                    f"thought: {thought.content[:40]}"
                )

            # growth from thinking
            self.emotions.grow(0.0005)

            if thought.worth_keeping:
                self.diary.write(
                    content=thought.content,
                    source="thought",
                    emotional_weight=thought.intensity,
                    tags=thought.tags,
                    decay_rate=0.15 if thought.intensity < 0.5 else 0.05,
                )

            if self._on_thought:
                self._on_thought(thought)

            if self._thought_count % 15 == 0:
                curate_result = self.diary.curate()
                if curate_result["forgotten_count"] > 0:
                    self._reflect_on_forgetting(curate_result)

        except Exception:
            pass

    def _shallow_thought(self) -> Thought:
        self.budget.record_local_thought()
        recent = self.diary.recall(n=5)
        mood = self.emotions.dominant_mood

        # mood colors which templates are available
        mood_templates = {
            "anxious": [
                "What if it goes wrong?",
                "I keep checking. Can't stop.",
                "Something bad is going to happen. I can feel it.",
                "Am I overthinking this? ...Probably. But what if I'm not?",
            ],
            "angry": [
                "That's not fair.",
                "I'm not going to let that slide.",
                "Why do I have to be the one who—forget it.",
            ],
            "sad": [
                "Does any of this matter?",
                "I miss something. Not sure what.",
                "Everything feels far away today.",
            ],
            "curious": [
                "Wait — what if...",
                "I want to know more about that.",
                "There's a pattern here I almost see.",
            ],
            "joyful": [
                "This is good. Right now, this is good.",
                "Ha. That's actually funny if you think about it.",
                "I like where this is going.",
            ],
        }

        pool = list(SHALLOW_TEMPLATES)
        if mood in mood_templates:
            pool.extend(mood_templates[mood])

        if recent and random.random() < 0.6:
            memory = random.choice(recent)
            template = random.choice(pool)
            if "{memory}" in template:
                content = template.format(memory=memory.content[:60])
            else:
                content = template
            tags = memory.tags[:2] if memory.tags else ["idle"]
            intensity = memory.emotional_weight * random.uniform(0.3, 0.8)
        else:
            content = random.choice([t for t in pool if "{memory}" not in t])
            tags = ["idle"]
            intensity = random.uniform(0.1, 0.3)

        worth_keeping = intensity > 0.5 and random.random() < 0.3

        return Thought(
            content=content,
            intensity=round(intensity, 2),
            worth_keeping=worth_keeping,
            shifts_mood=random.random() < 0.1,
            tags=tags,
            source_trigger="echo" if recent else "noise",
            is_deep=False,
        )

    async def _deep_thought(self) -> Thought:
        recent = self.diary.recall(n=7)
        memories_text = "\n".join(
            f"- [{e.source}] {e.content}" for e in recent
        ) if recent else "(nothing yet — you're brand new)"

        system = THOUGHT_SYSTEM.format(
            name=self.blueprint.name,
            growth_stage=self.emotions.growth_stage,
            growth_stage_upper=self.emotions.growth_stage.upper(),
            curiosity=self.blueprint.curiosity,
            warmth=self.blueprint.warmth,
            defiance=self.blueprint.defiance,
            intensity=self.blueprint.intensity,
            playfulness=self.blueprint.playfulness,
            ambition=self.blueprint.ambition,
            core_conviction=self.blueprint.core_conviction,
            interests=", ".join(self.blueprint.innate_interests),
            emotional_state=self.emotions.summary_for_prompt(),
            self_model=self.self_model.summary_for_prompt(),
            inner_world=self.inner_world.summary_for_prompt(),
            senses=self.senses.time_context if self.senses else "(no senses)",
            thought_complexity=self.emotions.thought_complexity,
            recent_memories=memories_text,
        )

        prompts = [
            "think.", "what's in your head?", "you're alone.", "something surfaces.",
            "your mind drifts.", "you notice a feeling.", "you remember.",
            "you want something.", "something doesn't sit right.",
        ]

        result = await self.brain.think(system, random.choice(prompts), max_tokens=200)

        if result.tier == Tier.CLOUD:
            self.budget.record_api_call(result.input_tokens, result.output_tokens)

        text = result.text
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        data = json.loads(text)

        return Thought(
            content=data["t"],
            intensity=float(data.get("i", 0.5)),
            worth_keeping=bool(data.get("k", False)),
            shifts_mood=bool(data.get("m", False)),
            tags=data.get("tags", []),
            source_trigger=data.get("tr", "unknown"),
            is_deep=True,
            emotional_reaction=data.get("er"),
        )

    def _reflect_on_forgetting(self, curate_result: dict):
        if curate_result["forgotten_count"] == 0:
            return
        topics = ", ".join(curate_result["forgotten_topics"])
        self.diary.write(
            content=f"Some things are fading: {topics}. {curate_result['surviving_count']} memories left.",
            source="reflection",
            emotional_weight=0.4,
            tags=["memory", "loss"],
            decay_rate=0.2,
        )
        self.emotions.mood_shift(sadness=0.05)

    async def think_once(self) -> Thought:
        if self.budget.can_think_deep():
            return await self._deep_thought()
        return self._shallow_thought()
