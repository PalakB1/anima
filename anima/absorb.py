"""
The Absorption Engine — the listening phase.

Before the agent speaks, it watches. Feed it:
- WhatsApp chat exports (.txt)
- Any chat logs
- Emails
- Journal entries
- Social media posts

It processes these silently, building:
- Understanding of the person's world
- Initial beliefs from observation
- Relationship models of people mentioned
- Communication patterns
- Emotional patterns
- Topics they care about

This is the newborn phase — eyes open, mouth closed.
"""

import json
import re
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass, field

from .diary import Diary
from .inner_world import InnerWorld
from .budget import Budget
from .brain import Brain, Tier


@dataclass
class AbsorptionResult:
    messages_processed: int
    messages_filtered: int = 0
    people_found: list[str] = field(default_factory=list)
    topics_found: list[str] = field(default_factory=list)
    emotional_patterns: list[str] = field(default_factory=list)
    beliefs_formed: int = 0
    relationships_built: int = 0


ABSORB_SYSTEM = """You are observing a person's conversations. You are a newborn mind
watching the world before you speak. You are NOT this person — you are watching them
to understand their world.

Read these messages carefully. You are looking for:

1. WHO are the important people? What's each relationship like?
2. WHAT does this person care about? What topics come up repeatedly?
3. HOW do they talk? Formal? Casual? Emoji-heavy? Long messages? Short?
4. WHAT are their emotional patterns? Do they get angry easily? Are they supportive? Anxious?
5. WHAT beliefs can you form about their world? "This person values X" "Their friend Y seems Z"
6. WHAT surprises you? What's unexpected or interesting?

You are building a model of this person's universe so you can eventually
be a meaningful peer in it — not a stranger who knows nothing.

OUTPUT THIS JSON:
{{
  "people": [
    {{"name": "person name", "relationship": "friend/family/partner/colleague/unknown",
      "model": "what they seem like based on messages", "trust_estimate": 0.0-1.0}}
  ],
  "topics": ["topic1", "topic2"],
  "communication_style": {{
    "formality": 0.0-1.0,
    "emoji_usage": 0.0-1.0,
    "message_length": "short/medium/long/mixed",
    "humor_type": "description of their humor",
    "patterns": ["specific patterns noticed"]
  }},
  "emotional_patterns": ["pattern1", "pattern2"],
  "beliefs_from_observation": [
    {{"content": "what you believe about this person/their world", "confidence": 0.0-1.0, "evidence": "what you saw"}}
  ],
  "interesting_observations": ["things that stood out"],
  "summary": "2-3 sentence summary of what you learned"
}}"""


class AbsorptionEngine:
    def __init__(self, diary: Diary, inner_world: InnerWorld, budget: Budget, brain: Brain):
        self.diary = diary
        self.inner_world = inner_world
        self.budget = budget
        self.brain = brain

    def absorb_whatsapp(self, file_path: Path) -> AbsorptionResult:
        """Parse and absorb a WhatsApp chat export."""
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        raw_count = len(re.findall(r"\d{1,2}/\d{1,2}/\d{2,4}", text))
        messages = self._parse_whatsapp(text)
        result = self._absorb_messages(messages, "whatsapp")
        result.messages_filtered = max(0, raw_count - len(messages))
        return result

    def absorb_text(self, text: str, source: str = "chat") -> AbsorptionResult:
        """Absorb any text — chat logs, journal entries, emails."""
        messages = [{"sender": "unknown", "content": line.strip(), "timestamp": ""}
                    for line in text.split("\n") if line.strip()]
        return self._absorb_messages(messages, source)

    def absorb_file(self, file_path: Path) -> AbsorptionResult:
        """Auto-detect format and absorb."""
        text = file_path.read_text(encoding="utf-8", errors="ignore")

        # detect WhatsApp format
        if re.search(r"\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}", text):
            return self.absorb_whatsapp(file_path)

        return self.absorb_text(text, source=file_path.stem)

    # messages that carry zero signal — skip entirely
    JUNK_PATTERNS = re.compile(
        r"^("
        r"ok|okay|okk+|k+|kk+|hmm+|hm+|haha+|lol+|lmao+|rofl|heh+|"
        r"yes|yeah+|yep|yup|ya+|no|nah+|nope|"
        r"hi|hey+|hello|hii+|bye+|gn|gm|good morning|good night|"
        r"👍|😂|😭|❤️|🔥|💀|🙏|😊|😅|🤣|👀|💯|"
        r"ok\?|sure|fine|cool+|nice+|great|wow+|oh+|ah+|ugh+|"
        r"thanks|thank you|thanku|thnx|ty|thx|"
        r"\.\.\.*|\.|\?|!+|\?\?+|"
        r"this message was deleted|"
        r"<media omitted>|<image omitted>|<video omitted>|<audio omitted>|"
        r"<sticker omitted>|<gif omitted>|<document omitted>|"
        r"missed voice call|missed video call|"
        r"you deleted this message|"
        r"messages and calls are end-to-end encrypted.*|"
        r"waiting for this message.*"
        r")$",
        re.IGNORECASE
    )

    # too short to carry meaning
    MIN_MEANINGFUL_LENGTH = 4

    def _is_junk(self, content: str) -> bool:
        stripped = content.strip()
        if len(stripped) < self.MIN_MEANINGFUL_LENGTH:
            return True
        if self.JUNK_PATTERNS.match(stripped):
            return True
        # pure emoji strings
        if all(not c.isalnum() and not c.isspace() for c in stripped):
            return True
        return False

    def _parse_whatsapp(self, text: str) -> list[dict]:
        """Parse WhatsApp export format."""
        messages = []
        pattern = r"(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2})\s*(?:am|pm|AM|PM)?\s*-\s*([^:]+):\s*(.*)"

        for match in re.finditer(pattern, text):
            date, time_str, sender, content = match.groups()
            if content.strip() and not self._is_junk(content):
                messages.append({
                    "sender": sender.strip(),
                    "content": content.strip(),
                    "timestamp": f"{date} {time_str}",
                })

        return messages

    def _absorb_messages(self, messages: list[dict], source: str = "chat") -> AbsorptionResult:
        """Process messages in chunks and build understanding."""
        if not messages:
            return AbsorptionResult(0, [], [], [], 0, 0)

        # pre-filter junk from non-WhatsApp sources too
        before_count = len(messages)
        messages = [m for m in messages if not self._is_junk(m["content"])]
        filtered_count = before_count - len(messages)

        if not messages:
            return AbsorptionResult(0, [], [], [], 0, 0)

        chunk_size = 50
        total_result = AbsorptionResult(
            messages_processed=len(messages),
            messages_filtered=filtered_count if source != "chat" else 0,
            people_found=[],
            topics_found=[],
            emotional_patterns=[],
            beliefs_formed=0,
            relationships_built=0,
        )

        for i in range(0, len(messages), chunk_size):
            chunk = messages[i:i + chunk_size]
            if not self.budget.can_think_deep():
                break

            chunk_text = "\n".join(
                f"[{m['timestamp']}] {m['sender']}: {m['content']}"
                if m['timestamp'] else f"{m['sender']}: {m['content']}"
                for m in chunk
            )

            try:
                analysis = self._analyze_chunk(chunk_text)
                self._apply_analysis(analysis, total_result)
            except Exception:
                continue

        # write a diary entry about the absorption
        self.diary.write(
            content=f"Watched {total_result.messages_processed} messages. "
                    f"Found {len(total_result.people_found)} people, "
                    f"{len(total_result.topics_found)} topics. Forming first impressions.",
            source="observation",
            emotional_weight=0.6,
            tags=["absorption", "beginning", "watching"],
            decay_rate=0.02,  # this is foundational — decays slowly
        )

        return total_result

    def _analyze_chunk(self, chunk_text: str) -> dict:
        result = asyncio.get_event_loop().run_until_complete(
            self.brain.analyze(
                ABSORB_SYSTEM,
                f"Observe these messages:\n\n{chunk_text}",
                max_tokens=600,
            )
        )

        if result.tier == Tier.CLOUD:
            self.budget.record_api_call(result.input_tokens, result.output_tokens)

        text = result.text
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)

    def _apply_analysis(self, analysis: dict, result: AbsorptionResult):
        # build relationships
        for person in analysis.get("people", []):
            name = person.get("name", "unknown")
            if name not in result.people_found:
                result.people_found.append(name)
            self.inner_world.update_relationship(
                name=name,
                model=person.get("model", "observed in messages"),
                trust_delta=0.0,
                valence=person.get("trust_estimate", 0.5),
                pattern=person.get("relationship", "unknown"),
            )
            result.relationships_built += 1

        # record topics
        for topic in analysis.get("topics", []):
            if topic not in result.topics_found:
                result.topics_found.append(topic)

        # record emotional patterns
        for pattern in analysis.get("emotional_patterns", []):
            if pattern not in result.emotional_patterns:
                result.emotional_patterns.append(pattern)

        # form beliefs from observation
        for belief in analysis.get("beliefs_from_observation", []):
            self.inner_world.add_belief(
                content=belief.get("content", ""),
                confidence=belief.get("confidence", 0.4),
                formed_from=f"observation: {belief.get('evidence', 'watching messages')}",
            )
            result.beliefs_formed += 1

        # store interesting observations in diary
        for obs in analysis.get("interesting_observations", []):
            self.diary.write(
                content=f"Noticed: {obs}",
                source="observation",
                emotional_weight=0.4,
                tags=["observation", "absorption"],
                decay_rate=0.1,
            )

        # store communication style insights
        style = analysis.get("communication_style", {})
        if style.get("patterns"):
            for p in style["patterns"][:2]:
                self.diary.write(
                    content=f"Communication pattern: {p}",
                    source="observation",
                    emotional_weight=0.3,
                    tags=["style", "communication"],
                    decay_rate=0.15,
                )
