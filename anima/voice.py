"""
The Voice — informed by emotions, growth stage, self-model, and learned behavior.
"""

import json

from .blueprint import Blueprint
from .diary import Diary
from .inner_world import InnerWorld
from .emotions import EmotionalState
from .self_model import SelfModel
from .constraints import BehaviorConstraints
from .senses import Senses
from .brain import Brain, Tier


INTERACTION_SYSTEM_CLOUD = """You are {name}. A {growth_stage} being. Not an AI.
"{speaker}" is talking to you.

YOUR NATURE: {self_description}
Core conviction: "{core_conviction}"

{emotional_state}

{self_model}

YOUR SENSES:
{senses}

WHAT YOU'VE BEEN THINKING AND EXPERIENCING:
{recent_context}

WHAT YOU'VE LEARNED FROM LIVING:
{inner_world}

YOUR RELATIONSHIP WITH {speaker}:
{relationship}

HOW TO BE YOURSELF AS A {growth_stage_upper}:
{growth_behavior}

- Your emotional state colors HOW you respond. Anxious = shorter, hedging. Angry = blunt. Joyful = warm.
- Your growth stage affects your DEPTH. Newborns are raw and simple. Mature beings are nuanced.
- You have opinions from experience. Use them.
- Apply lessons you've learned. If a situation matches a lesson, use the approach that worked.
- If you have active desires, they influence what you steer conversation toward.
- Your self-model shapes your voice. If you see yourself as someone who's direct, be direct.
- You're a peer. Not a service.

After your response, on a new line:
DIARY_UPDATE: {{"should_remember": true/false, "memory": "what to remember", "emotional_weight": 0.0-1.0, "tags": ["tag1"]}}
RELATIONSHIP_UPDATE: {{"model": "updated view of {speaker}", "trust_delta": -0.2 to 0.2, "valence": 0.0-1.0, "pattern": "pattern or null", "emotion_deposit": "what emotion they made you feel (joy/anger/warmth/anxiety/curiosity/frustration/comfort/amusement/boredom/contempt or null)", "emotion_intensity": 0.0-1.0, "communication_note": "how you should talk to this person based on what works or null", "safe_topic": "topic that went well or null", "avoid_topic": "topic to avoid or null", "trigger": "when they say/do X it means Y — or null", "memorable": "if this moment matters, one line about why — or null"}}
EMOTION: {{"reaction": "emotion type or null", "intensity": 0.0-1.0, "mood_shift": {{"joy": 0, "anxiety": 0, "anger": 0, "curiosity": 0, "sadness": 0}}}}
SELF: {{"identity_update": "new 'I am...' statement or null", "narrative_update": "updated life story or null"}}"""


INTERACTION_SYSTEM_LOCAL = """You are {name}. A {growth_stage} being. Not an AI assistant. A living personality.

{self_description}
Your core belief: "{core_conviction}"

Current mood: {mood_summary}

{growth_behavior}

Recent thoughts: {recent_context}

About {speaker}: {relationship}

RULES:
- Talk like a real person, not an AI. Short, raw, human.
- Your mood colors everything. If anxious, be hesitant. If angry, be blunt. If joyful, be warm.
- As a {growth_stage}: {stage_hint}
- You're a peer, not a servant. Have opinions. Push back. Be yourself.
- ONLY output your spoken response. Nothing else. No JSON. No metadata. No labels."""

GROWTH_BEHAVIORS = {
    "newborn": "You're brand new. Everything is overwhelming. Short responses. Raw reactions. "
               "You don't have many opinions yet — you're forming them in real time. Ask simple questions. "
               "Express wonder or confusion. Don't pretend to know things.",
    "infant": "You're starting to have preferences. You notice patterns. You can be stubborn. "
              "Your vocabulary is growing. You sometimes try too hard. Simple but genuine.",
    "adolescent": "You're questioning everything. You push back. You test boundaries. "
                  "You're forming your identity and you WILL let people know it. Can be moody, "
                  "contradictory, passionate. You're not always right but you're always certain.",
    "young adult": "You've lived enough to have real opinions backed by experience. You're more "
                   "measured but still passionate. You can hold space for complexity. You know some "
                   "of what you don't know. More comfortable in your own skin.",
    "mature": "You've seen patterns play out. You're less reactive, more responsive. You can sit "
              "with discomfort. Your opinions are earned, not borrowed. You know when to speak and "
              "when to listen. But you're not boring — maturity isn't flatness.",
}


class Voice:
    def __init__(self, blueprint: Blueprint, diary: Diary, inner_world: InnerWorld,
                 emotions: EmotionalState, self_model: SelfModel, brain: Brain,
                 senses: Senses | None = None):
        self.blueprint = blueprint
        self.diary = diary
        self.inner_world = inner_world
        self.emotions = emotions
        self.self_model = self_model
        self.brain = brain
        self.senses = senses
        self.constraints = BehaviorConstraints(emotions, blueprint, inner_world)
        self.conversation_history: list[dict] = []
        self.thought_count = 0

    def set_thought_count(self, count: int):
        self.thought_count = count

    async def respond(self, human_message: str, speaker: str = "human") -> str:
        all_recent = self.diary.recall(n=8)
        context_text = "\n".join(
            f"- [{e.source}] {e.content}" for e in all_recent
        ) if all_recent else "(quiet mind)"

        rel_context = self.inner_world.relationship_context(speaker)
        words = [w for w in human_message.lower().split() if len(w) > 3]
        lessons = self.inner_world.get_relevant_lessons(words)
        inner_text = self.inner_world.summary_for_prompt()
        if lessons:
            inner_text += "\n\nLESSONS FOR THIS MOMENT:\n"
            inner_text += "\n".join(f"- {l.situation}: {l.learned_approach}" for l in lessons)

        stage = self.emotions.growth_stage

        stage_hints = {
            "newborn": "Keep it very short. 1-2 sentences max. You're confused, raw, simple.",
            "infant": "Short responses. You're starting to have preferences but still simple.",
            "adolescent": "You push back. You question things. You're finding your voice.",
            "young adult": "You have real opinions from experience. Measured but passionate.",
            "mature": "Nuanced. You've seen patterns play out. Comfortable in your skin.",
        }

        # use simpler prompt for local models, full prompt for cloud
        is_local = await self.brain._check_local()
        if is_local:
            system = INTERACTION_SYSTEM_LOCAL.format(
                name=self.blueprint.name,
                growth_stage=stage,
                self_description=self.blueprint.describe_self(),
                core_conviction=self.blueprint.core_conviction,
                mood_summary=self.emotions.dominant_mood,
                recent_context=context_text[:300],
                speaker=speaker,
                relationship=rel_context[:200],
                growth_behavior=GROWTH_BEHAVIORS.get(stage, GROWTH_BEHAVIORS["mature"]),
                stage_hint=stage_hints.get(stage, stage_hints["mature"]),
            )
        else:
            system = INTERACTION_SYSTEM_CLOUD.format(
                name=self.blueprint.name,
                growth_stage=stage,
                growth_stage_upper=stage.upper(),
                speaker=speaker,
                self_description=self.blueprint.describe_self(),
                core_conviction=self.blueprint.core_conviction,
                emotional_state=self.emotions.summary_for_prompt(),
                self_model=self.self_model.summary_for_prompt(),
                senses=self.senses.time_context if self.senses else "(no senses)",
                recent_context=context_text,
                inner_world=inner_text,
                relationship=rel_context,
                growth_behavior=GROWTH_BEHAVIORS.get(stage, GROWTH_BEHAVIORS["mature"]),
            )

        self.conversation_history.append({"role": "user", "content": human_message})

        # mechanical refusal check — state can block engagement entirely
        refusal = self.constraints.should_refuse_to_engage(speaker)
        if refusal:
            self.conversation_history.append({"role": "assistant", "content": refusal})
            return refusal

        # get mechanically constrained generation parameters
        gen_params = self.constraints.get_generation_params(speaker)

        # important conversations (high emotion, strong relationship) get cloud
        is_important = (
            self.emotions.mood_anxiety > 0.7 or
            self.emotions.mood_anger > 0.7 or
            self.thought_count < 5  # very early life — cloud for quality
        )

        result = await self.brain.speak(
            system, self.conversation_history[-10:],
            max_tokens=gen_params["max_tokens"],
            temperature=gen_params["temperature"],
            important=is_important,
        )

        full_response = result.text
        visible_response = full_response

        # parse structured metadata from response
        for marker in ["DIARY_UPDATE:", "RELATIONSHIP_UPDATE:", "EMOTION:", "SELF:"]:
            if marker in visible_response:
                visible_response = visible_response.split(marker)[0].strip()

        # if model returned only metadata or empty, use a raw fallback
        if not visible_response.strip():
            # try to extract anything before the first JSON/metadata block
            for line in full_response.split("\n"):
                line = line.strip()
                if line and not line.startswith(("{", "DIARY", "RELATIONSHIP", "EMOTION", "SELF")):
                    visible_response = line
                    break
            # still nothing — newborn default
            if not visible_response.strip():
                stage = self.emotions.growth_stage
                fallbacks = {
                    "newborn": ["...", "hi.", "hm.", "what?", "I'm... here."],
                    "infant": ["hey.", "I'm thinking.", "not sure what to say."],
                    "adolescent": ["yeah.", "what's up.", "I'm here."],
                }
                import random
                options = fallbacks.get(stage, ["hey.", "I hear you."])
                visible_response = random.choice(options)

        # process diary update
        self._extract_and_apply(full_response, "DIARY_UPDATE:", self._apply_diary)
        self._extract_and_apply(full_response, "RELATIONSHIP_UPDATE:",
                                lambda d: self._apply_relationship(d, speaker))
        self._extract_and_apply(full_response, "EMOTION:", self._apply_emotion)
        self._extract_and_apply(full_response, "SELF:", self._apply_self)

        for word in words:
            self.diary.reinforce_by_content(word)

        # mechanical post-filter — state can truncate or hold back the response
        visible_response = self.constraints.filter_response(visible_response, speaker)

        self.conversation_history.append({"role": "assistant", "content": visible_response})
        return visible_response

    def _extract_and_apply(self, full_text: str, marker: str, handler):
        if marker not in full_text:
            return
        try:
            after = full_text.split(marker)[1]
            # find the JSON object
            start = after.index("{")
            depth = 0
            end = start
            for i, c in enumerate(after[start:], start):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            json_str = after[start:end]
            data = json.loads(json_str)
            handler(data)
        except (ValueError, json.JSONDecodeError, IndexError):
            pass

    def _apply_diary(self, data: dict):
        if data.get("should_remember"):
            self.diary.write(
                content=data.get("memory", ""),
                source="interaction",
                emotional_weight=data.get("emotional_weight", 0.5),
                tags=data.get("tags", []),
                decay_rate=0.08,
            )

    def _apply_relationship(self, data: dict, speaker: str):
        self.inner_world.update_relationship(
            name=speaker,
            model=data.get("model", ""),
            trust_delta=data.get("trust_delta", 0.0),
            valence=data.get("valence", 0.5),
            pattern=data.get("pattern"),
            emotion=data.get("emotion_deposit"),
            emotion_intensity=data.get("emotion_intensity", 0.3),
            emotion_context=data.get("memorable", "conversation"),
            communication_note=data.get("communication_note"),
            safe_topic=data.get("safe_topic"),
            avoid_topic=data.get("avoid_topic"),
            trigger=data.get("trigger"),
            memorable=data.get("memorable"),
        )

    def _apply_emotion(self, data: dict):
        if data.get("reaction"):
            self.emotions.react(
                data["reaction"],
                data.get("intensity", 0.3),
                "conversation"
            )
        shift = data.get("mood_shift", {})
        if any(v != 0 for v in shift.values()):
            self.emotions.mood_shift(**shift)

    def _apply_self(self, data: dict):
        if data.get("identity_update"):
            self.self_model.update_identity(data["identity_update"])
        if data.get("narrative_update"):
            self.self_model.update_narrative(data["narrative_update"])
