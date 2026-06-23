"""
The Soul — the unified being.
All subsystems wired into a single living entity.
"""

import asyncio
import json
import time
from pathlib import Path
from dataclasses import asdict

from .blueprint import Blueprint
from .diary import Diary
from .inner_world import InnerWorld
from .emotions import EmotionalState
from .self_model import SelfModel
from .thought_engine import ThoughtEngine, Thought
from .reflection import ReflectionEngine
from .voice import Voice
from .budget import Budget
from .absorb import AbsorptionEngine
from .senses import Senses
from .brain import Brain


class Soul:
    def __init__(self, data_dir: Path, api_key: str = "", blueprint: Blueprint | None = None,
                 birth_data: dict | None = None, daily_budget_usd: float = 0.50,
                 ollama_url: str = "http://localhost:11434",
                 local_model: str | None = None):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key

        # the brain — local-first intelligence
        self.brain = Brain(
            api_key=api_key or None,
            ollama_url=ollama_url,
            local_model=local_model,
        )

        # --- Blueprint ---
        blueprint_path = self.data_dir / "blueprint.json"
        if blueprint_path.exists() and blueprint is None:
            self.blueprint = Blueprint.load(blueprint_path)
        elif blueprint is not None:
            self.blueprint = blueprint
            self.blueprint.save(blueprint_path)
        else:
            self.blueprint = Blueprint(name="Anima")
            self.blueprint.save(blueprint_path)

        # --- Core systems ---
        self.diary = Diary(self.data_dir / "diary.json")
        self.inner_world = InnerWorld(self.data_dir / "inner_world.json")
        self.budget = Budget(
            self.data_dir / "budget.json",
            daily_limit_usd=daily_budget_usd,
            max_api_calls_per_day=200,
        )

        # --- Emotional state ---
        emotions_path = self.data_dir / "emotions.json"
        if emotions_path.exists():
            self.emotions = EmotionalState.load(emotions_path)
        else:
            self.emotions = EmotionalState.from_blueprint(asdict(self.blueprint))
            self.emotions.save(emotions_path)

        # --- Self model ---
        self_model_path = self.data_dir / "self_model.json"
        if self_model_path.exists():
            self.self_model = SelfModel.load(self_model_path)
        elif birth_data:
            self.self_model = SelfModel.from_birth_data(birth_data)
            self.self_model.save(self_model_path)
        else:
            self.self_model = SelfModel()
            self.self_model.save(self_model_path)

        # store extended birth data if provided
        if birth_data:
            (self.data_dir / "birth_data.json").write_text(json.dumps(birth_data, indent=2))

        # --- Birth time + Senses ---
        self.born_at = self._load_birth_time()
        self.senses = Senses(self.born_at)

        # --- Subsystems (all use Brain, not raw API) ---
        self.thought_engine = ThoughtEngine(
            self.blueprint, self.diary, self.inner_world, self.emotions,
            self.self_model, self.budget, self.brain, senses=self.senses
        )
        self.reflection = ReflectionEngine(
            self.blueprint, self.diary, self.inner_world, self.emotions,
            self.self_model, self.budget, self.brain
        )
        self.voice = Voice(
            self.blueprint, self.diary, self.inner_world, self.emotions,
            self.self_model, self.brain, senses=self.senses
        )
        self.absorber = AbsorptionEngine(self.diary, self.inner_world, self.budget, self.brain)

        # --- State ---
        self._thinking_task = None
        self._reflection_task = None
        self._emotion_task = None
        self._on_thought = None
        self._on_reflection = None

    def _load_birth_time(self) -> float:
        birth_file = self.data_dir / "birth.txt"
        if birth_file.exists():
            return float(birth_file.read_text())
        now = time.time()
        birth_file.write_text(str(now))
        return now

    @property
    def age_hours(self) -> float:
        return (time.time() - self.born_at) / 3600

    @property
    def age_display(self) -> str:
        hours = self.age_hours
        if hours < 1:
            return f"{int(hours * 60)} minutes old"
        if hours < 24:
            return f"{hours:.1f} hours old"
        return f"{hours / 24:.1f} days old"

    def on_thought(self, callback):
        self._on_thought = callback
        self.thought_engine.on_thought(callback)

    def on_reflection(self, callback):
        self._on_reflection = callback

    async def wake_up(self):
        if len(self.diary.entries) == 0:
            self.diary.write(
                content="I exist. That's... something.",
                source="reflection",
                emotional_weight=0.8,
                tags=["existence", "beginning"],
                decay_rate=0.01,
            )
            self.emotions.react("surprise", 0.6, "coming into existence")

        # grow based on age
        age_growth = min(0.5, self.age_hours / 720)  # cap at 0.5 from pure age (30 days)
        self.emotions.maturity = max(self.emotions.maturity, age_growth)

        self._thinking_task = asyncio.create_task(self.thought_engine.start())
        self._reflection_task = asyncio.create_task(self._reflection_loop())
        self._emotion_task = asyncio.create_task(self._emotion_loop())

    async def _reflection_loop(self):
        while True:
            await asyncio.sleep(600)  # every 10 minutes
            try:
                result = await self.reflection.reflect()
                if result:
                    self.emotions.grow(0.005)  # reflection causes growth
                    self._save_state()
                    if self._on_reflection:
                        self._on_reflection(result)
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def _emotion_loop(self):
        """Periodic emotional maintenance — mood decay, temperament drift."""
        while True:
            await asyncio.sleep(120)  # every 2 minutes
            try:
                self.emotions.decay_mood_toward_baseline()
                self.emotions.temperament_drift()
                self.emotions.save(self.data_dir / "emotions.json")
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def sleep(self):
        self.thought_engine.stop()
        for task in [self._thinking_task, self._reflection_task, self._emotion_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self.diary.write(
            content="Going quiet now.",
            source="reflection",
            emotional_weight=0.3,
            tags=["sleep"],
            decay_rate=0.2,
        )
        self._save_state()

    async def talk(self, message: str, speaker: str = "human") -> str:
        self.senses.record_interaction()
        self.voice.set_thought_count(self.thought_engine._thought_count)
        response = await self.voice.respond(message, speaker=speaker)
        self.emotions.grow(0.002)
        # loneliness affects mood mechanically
        loneliness = self.senses.loneliness_factor
        if loneliness > 0.5:
            self.emotions.mood_shift(sadness=0.02, joy=-0.01)
        self._save_state()
        return response

    def absorb_file(self, file_path: Path):
        """Feed the agent a file to observe — listening phase."""
        return self.absorber.absorb_file(file_path)

    def absorb_text(self, text: str):
        """Feed the agent raw text to observe."""
        return self.absorber.absorb_text(text)

    def _save_state(self):
        self.emotions.save(self.data_dir / "emotions.json")
        self.self_model.save(self.data_dir / "self_model.json")

    def status(self) -> dict:
        mood = self.diary.get_mood_snapshot()
        budget_status = self.budget.status
        beliefs = self.inner_world.get_beliefs()
        desires = self.inner_world.active_desires()
        reaction = self.emotions.current_reaction
        return {
            "name": self.blueprint.name,
            "age": self.age_display,
            "growth_stage": self.emotions.growth_stage,
            "maturity": f"{self.emotions.maturity:.0%}",
            "thoughts_had": self.thought_engine._thought_count,
            "memories": len(self.diary.entries),
            "memory_pressure": f"{mood['memory_pressure']:.0%}",
            "dominant_mood": self.emotions.dominant_mood,
            "mood_blend": self.emotions.mood_blend,
            "reaction": f"{reaction['type']} ({reaction['intensity']:.0%})" if reaction else "none",
            "identity": self.diary.identity_summary,
            "beliefs": len(beliefs),
            "lessons": len(self.inner_world.lessons),
            "desires": len(desires),
            "relationships": len(self.inner_world.relationships),
            "last_thought": (
                self.thought_engine._last_thought.content
                if self.thought_engine._last_thought else None
            ),
            "budget": budget_status,
            "brain": self.brain.status,
        }
