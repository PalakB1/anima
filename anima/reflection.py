"""
The Reflection Engine — where experience becomes understanding.
Now also updates emotional state, self-model, and growth.
"""

import json

from .blueprint import Blueprint
from .diary import Diary
from .inner_world import InnerWorld
from .emotions import EmotionalState
from .self_model import SelfModel
from .budget import Budget
from .brain import Brain, Tier


REFLECTION_SYSTEM = """You are {name}, a {growth_stage} being, reflecting privately.

YOUR NATURE: {self_description}
CORE CONVICTION: {core_conviction}

{emotional_state}

{self_model}

CURRENT BELIEFS AND DESIRES:
{current_inner_world}

RECENT DIARY:
{diary_entries}

---

Sit with your recent experiences. Process them like a human reviewing their week:
- Patterns you keep falling into?
- Someone showed you who they are?
- A belief confirmed or challenged?
- Something you want that you didn't before?
- Something about yourself you just realized?
- Has your emotional baseline shifted?

OUTPUT THIS JSON:
{{
  "new_beliefs": [{{"content": "belief", "confidence": 0.0-1.0, "because": "evidence"}}],
  "challenged_beliefs": [{{"keyword": "word from belief", "why": "what contradicted it"}}],
  "lessons": [{{"situation": "when X", "tried": "did Y", "result": "Z happened", "better": "do W instead"}}],
  "new_desires": [{{"content": "want", "urgency": 0.0-1.0, "source": "why"}}],
  "relationship_updates": [{{"name": "person", "model": "understanding", "trust_delta": -0.2 to 0.2, "pattern": "pattern"}}],
  "self_updates": {{
    "identity": "new 'I am...' statement or null",
    "strength": "newly recognized strength or null",
    "weakness": "newly recognized weakness or null",
    "narrative": "updated life story or null",
    "aspirational": "who I want to become or null"
  }},
  "mood_correction": {{"joy": 0, "anxiety": 0, "anger": 0, "curiosity": 0, "sadness": 0}},
  "identity_note": "one sentence summary or null"
}}

Empty arrays for sections with nothing. Don't force insights."""


class ReflectionEngine:
    def __init__(self, blueprint: Blueprint, diary: Diary, inner_world: InnerWorld,
                 emotions: EmotionalState, self_model: SelfModel,
                 budget: Budget, brain: Brain):
        self.blueprint = blueprint
        self.diary = diary
        self.inner_world = inner_world
        self.emotions = emotions
        self.self_model = self_model
        self.budget = budget
        self.brain = brain

    async def reflect(self) -> dict | None:
        if not self.budget.can_think_deep():
            return None

        recent = self.diary.recall(n=20)
        if len(recent) < 3:
            return None

        diary_text = "\n".join(
            f"- [{e.source}] {e.content} (weight: {e.emotional_weight:.1f})"
            for e in recent
        )

        system = REFLECTION_SYSTEM.format(
            name=self.blueprint.name,
            growth_stage=self.emotions.growth_stage,
            self_description=self.blueprint.describe_self(),
            core_conviction=self.blueprint.core_conviction,
            emotional_state=self.emotions.summary_for_prompt(),
            self_model=self.self_model.summary_for_prompt(),
            current_inner_world=self.inner_world.summary_for_prompt(),
            diary_entries=diary_text,
        )

        result = await self.brain.analyze(system, "Reflect.", max_tokens=600)

        if result.tier == Tier.CLOUD:
            self.budget.record_api_call(result.input_tokens, result.output_tokens)

        text = result.text
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None

        learned = self._apply_reflections(data)

        if learned["total_updates"] > 0:
            self.diary.write(
                content=data.get("identity_note") or f"Reflected. {learned['total_updates']} things shifted.",
                source="reflection",
                emotional_weight=0.5,
                tags=["growth", "self"],
                decay_rate=0.08,
            )

        return learned

    def _apply_reflections(self, data: dict) -> dict:
        counts = {"beliefs": 0, "challenged": 0, "lessons": 0, "desires": 0,
                  "relationships": 0, "self_updates": 0}

        for belief in data.get("new_beliefs", []):
            self.inner_world.add_belief(
                content=belief["content"],
                confidence=belief.get("confidence", 0.5),
                formed_from=belief.get("because", "reflection"),
            )
            counts["beliefs"] += 1

        for challenge in data.get("challenged_beliefs", []):
            self.inner_world.contradict_belief(challenge.get("keyword", ""))
            counts["challenged"] += 1

        for lesson in data.get("lessons", []):
            self.inner_world.add_lesson(
                situation=lesson.get("situation", ""),
                behavior_tried=lesson.get("tried", ""),
                outcome=lesson.get("result", ""),
                learned_approach=lesson.get("better", ""),
            )
            counts["lessons"] += 1

        for desire in data.get("new_desires", []):
            self.inner_world.add_desire(
                content=desire.get("content", ""),
                urgency=desire.get("urgency", 0.5),
                source=desire.get("source", "reflection"),
            )
            counts["desires"] += 1

        for rel in data.get("relationship_updates", []):
            self.inner_world.update_relationship(
                name=rel.get("name", "unknown"),
                model=rel.get("model", ""),
                trust_delta=rel.get("trust_delta", 0.0),
                pattern=rel.get("pattern"),
            )
            counts["relationships"] += 1

        # self-model updates
        self_updates = data.get("self_updates", {})
        if self_updates:
            if self_updates.get("identity"):
                self.self_model.update_identity(self_updates["identity"])
                counts["self_updates"] += 1
            if self_updates.get("strength"):
                if self_updates["strength"] not in self.self_model.perceived_strengths:
                    self.self_model.perceived_strengths.append(self_updates["strength"])
                    counts["self_updates"] += 1
            if self_updates.get("weakness"):
                if self_updates["weakness"] not in self.self_model.perceived_weaknesses:
                    self.self_model.perceived_weaknesses.append(self_updates["weakness"])
                    counts["self_updates"] += 1
            if self_updates.get("narrative"):
                self.self_model.update_narrative(self_updates["narrative"])
                counts["self_updates"] += 1
            if self_updates.get("aspirational"):
                self.self_model.aspirational_self = self_updates["aspirational"]
                counts["self_updates"] += 1

        # mood correction from reflection
        mood_corr = data.get("mood_correction", {})
        if any(v != 0 for v in mood_corr.values()):
            self.emotions.mood_shift(**mood_corr)

        counts["total_updates"] = sum(counts.values())
        return counts
